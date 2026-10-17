from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import src.web
from src.core.personal import Personal
from src.core.usuarios import User
from src.web.controllers.personal import personal_bp
from src.web.services.importacion_personal import procesar_csv_personal


ENCABEZADO = "dni,nombre,apellido,tipo_personal,sector,menu\n"


def test_csv_vacio_devuelve_error_de_archivo():
    resultado = procesar_csv_personal("")

    assert resultado["procesados"] == 0
    assert resultado["importados"] == 0
    assert resultado["rechazados"] == 0
    assert resultado["errores"][0]["fila"] is None
    assert resultado["errores"][0]["detalles"][0]["campo"] == "Archivo"


def test_encabezado_invalido_informa_columnas_faltantes():
    resultado = procesar_csv_personal("dni,nombre\n12345678,Ana\n")

    assert resultado["procesados"] == 0
    assert resultado["importados"] == 0
    assert resultado["rechazados"] == 0
    assert resultado["errores"][0]["fila"] is None
    motivos = [
        detalle["motivo"]
        for detalle in resultado["errores"][0]["detalles"]
    ]
    assert any("Falta la columna 'apellido'" in motivo for motivo in motivos)


def test_procesa_filas_validas_y_rechazadas_y_resume_resultados():
    contenido = (
        ENCABEZADO
        + "12345678,Ana,Perez,Personal Fijo,Quirófano,General\n"
        + "87654321,Juan,Gomez,Tipo Invalido,,General\n"
    )
    datos_validos = SimpleNamespace(
        dni="12345678",
        nombre="Ana",
        apellido="Perez",
        model_dump=lambda: {"dni": "12345678", "nombre": "Ana"},
    )

    with (
        patch(
            "src.web.services.importacion_personal.validar_fila_csv",
            side_effect=[
                (datos_validos, {}),
                (None, {"tipo_personal_id": "El tipo no existe."}),
            ],
        ),
        patch.object(Personal, "crear_personal") as crear,
    ):
        resultado = procesar_csv_personal(contenido)

    assert resultado["procesados"] == 2
    assert resultado["importados"] == 1
    assert resultado["rechazados"] == 1
    assert resultado["filas_importadas"] == [
        {
            "fila": 2,
            "nombre": "Ana",
            "apellido": "Perez",
            "tipo_personal": "Personal Fijo",
            "sector": "Quirófano",
            "menu": "General",
        }
    ]
    assert resultado["errores"][0]["fila"] == 3
    assert resultado["errores"][0]["detalles"] == [
        {
            "campo": "tipo de personal",
            "motivo": "El tipo no existe.",
        }
    ]
    crear.assert_called_once_with({"dni": "12345678", "nombre": "Ana"})


def test_fila_con_columnas_extra_se_rechaza_con_motivo():
    contenido = ENCABEZADO + "12345678,Ana,Perez,Personal Fijo,Sector,General,extra\n"

    with patch(
        "src.web.services.importacion_personal.validar_fila_csv"
    ) as validar:
        resultado = procesar_csv_personal(contenido)

    assert resultado["procesados"] == 1
    assert resultado["importados"] == 0
    assert resultado["rechazados"] == 1
    assert "Sobran 1 columna(s)" in resultado["errores"][0]["detalles"][0]["motivo"]
    validar.assert_not_called()


def test_controller_delega_procesamiento_al_service():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(personal_bp)
    client = app.test_client()

    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_role"] = "Administrador"

    resultado_esperado = {
        "procesados": 0,
        "importados": 0,
        "rechazados": 0,
        "filas_importadas": [],
        "errores": [],
    }
    contenido = ENCABEZADO.encode("utf-8")

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch(
            "src.web.controllers.personal.procesar_csv_personal",
            return_value=resultado_esperado,
        ) as procesar,
        patch(
            "src.web.controllers.personal.render_template",
            return_value="renderizado",
        ) as renderizar,
    ):
        response = client.post(
            "/personal/importar",
            data={
                "archivo_csv": (
                    BytesIO(contenido),
                    "personal.csv",
                )
            },
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    procesar.assert_called_once_with(ENCABEZADO)
    renderizar.assert_called_once_with(
        "personal/personal_importar.html",
        active_page="personal",
        resultado=resultado_esperado,
    )
