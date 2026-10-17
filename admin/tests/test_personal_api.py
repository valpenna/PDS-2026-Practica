from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
import pytest

import src.web
from src.core.personal import Personal
from src.core.roles import NombreRol
from src.core.sectores import Sector
from src.core.tipos_menu import TipoMenu
from src.core.tipos_personal import TipoPersonal
from src.core.usuarios import User
from src.web.api.personal import personal_api_bp, personal_sector_api_bp


def crear_cliente():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(personal_api_bp)
    app.register_blueprint(personal_sector_api_bp)
    return app.test_client()


def usuario(rol, sector_id=1):
    return SimpleNamespace(
        rol=SimpleNamespace(nombre=rol.value),
        sector_id=sector_id,
        activo=True,
    )


def solicitar(client, metodo, ruta, usuario_actual, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = "Bearer token-de-prueba"

    with (
        patch(
            "src.web.api.helpers.decodificar_token",
            return_value={"sub": "1"},
        ),
        patch.object(User, "obtener_por_id", return_value=usuario_actual),
    ):
        return getattr(client, metodo)(ruta, headers=headers, **kwargs)


def persona(
    *,
    person_id=7,
    dni="12345678",
    tipo_personal_id=1,
    sector_id=3,
    menu_id=1,
    activo=True,
):
    return SimpleNamespace(
        id=person_id,
        dni=dni,
        nombre="Ana",
        apellido="Pérez",
        tipo_personal_id=tipo_personal_id,
        sector_id=sector_id,
        menu_id=menu_id,
        activo=activo,
    )


def tipo_personal(tipo_id=1, nombre="Personal Fijo"):
    return SimpleNamespace(id=tipo_id, nombre=nombre)


def tipo_menu():
    return SimpleNamespace(id=1, nombre="General")


def sector(sector_id=3, nombre="Quirófano", activo=True):
    return SimpleNamespace(id=sector_id, nombre=nombre, activo=activo)


def datos_personal(
    *,
    dni="12345678",
    tipo_personal_id=1,
    sector_id=3,
):
    return {
        "dni": dni,
        "nombre": "Ana",
        "apellido": "Pérez",
        "tipo_personal_id": tipo_personal_id,
        "menu_id": 1,
        "sector_id": sector_id,
    }


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos"),
    [
        ("get", "/api/personnel", None),
        ("get", "/api/personnel/7", None),
        ("get", "/api/sectors/3/personnel", None),
        ("post", "/api/personnel", {}),
        ("put", "/api/personnel/7", {}),
        ("delete", "/api/personnel/7", None),
    ],
)
def test_todos_los_endpoints_personal_requieren_token(metodo, ruta, datos):
    client = crear_cliente()

    if datos is None:
        response = getattr(client, metodo)(ruta)
    else:
        response = getattr(client, metodo)(ruta, json=datos)

    assert response.status_code == 401
    assert "error" in response.json


@pytest.mark.parametrize(
    ("metodo", "ruta", "datos"),
    [
        ("get", "/api/personnel", None),
        ("get", "/api/personnel/7", None),
        ("get", "/api/sectors/3/personnel", None),
        ("post", "/api/personnel", {}),
        ("put", "/api/personnel/7", {}),
        ("delete", "/api/personnel/7", None),
    ],
)
def test_todos_los_endpoints_personal_rechazan_rol_no_autorizado(
    metodo, ruta, datos
):
    client = crear_cliente()
    administrador = usuario(NombreRol.ADMINISTRADOR)

    if datos is None:
        response = solicitar(client, metodo, ruta, administrador)
    else:
        response = solicitar(
            client,
            metodo,
            ruta,
            administrador,
            json=datos,
        )

    assert response.status_code == 403
    assert "error" in response.json


def test_listar_personal_rechaza_rol_no_autorizado():
    client = crear_cliente()

    response = solicitar(
        client,
        "get",
        "/api/personnel",
        usuario(NombreRol.ADMINISTRADOR),
    )

    assert response.status_code == 403
    assert "error" in response.json


def test_listar_personal_limita_jefe_a_su_sector_y_residentes_y_pagina():
    client = crear_cliente()
    jefe = usuario(NombreRol.JEFE_SERVICIO, sector_id=3)
    registro = persona()

    with patch.object(
        Personal,
        "buscar",
        return_value=([(registro, "Personal Fijo", "Quirófano", "General")], 1),
    ) as buscar:
        response = solicitar(
            client,
            "get",
            "/api/personnel?sector_id=99&page=2&per_page=5&dni=123",
            jefe,
        )

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["page"] == 2
    assert response.json["per_page"] == 5
    assert response.json["data"][0]["dni"] == "12345678"
    assert response.json["data"][0]["sector"]["nombre"] == "Quirófano"
    filtros = buscar.call_args.args[0]
    assert filtros.sector_id is None
    assert filtros.sector_jefe_id == 3
    assert filtros.solo_residentes is False
    assert filtros.dni == "123"
    assert filtros.pagina == 2
    assert filtros.por_pagina == 5


def test_listar_personal_rechaza_filtros_invalidos():
    client = crear_cliente()

    response = solicitar(
        client,
        "get",
        "/api/personnel?page=0",
        usuario(NombreRol.ALIMENTACION),
    )

    assert response.status_code == 400
    assert response.json["error"]["code"] == "validation_error"


def test_detalle_permite_a_jefe_consultar_residente():
    client = crear_cliente()
    residente = persona(tipo_personal_id=2, sector_id=None)

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=residente),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(2, "Residente"),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
    ):
        response = solicitar(
            client,
            "get",
            "/api/personnel/7",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
        )

    assert response.status_code == 200
    assert response.json["tipo_personal"]["nombre"] == "Residente"
    assert response.json["sector"] is None


def test_detalle_rechaza_a_jefe_personal_de_otro_sector():
    client = crear_cliente()
    persona_ajena = persona(sector_id=9)

    with (
        patch.object(
            Personal,
            "obtener_personal_por_id",
            return_value=persona_ajena,
        ),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
    ):
        response = solicitar(
            client,
            "get",
            "/api/personnel/7",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
        )

    assert response.status_code == 403
    assert response.json["error"]["code"] == "http_403"


def test_detalle_inexistente_devuelve_404_json():
    client = crear_cliente()

    with patch.object(Personal, "obtener_personal_por_id", return_value=None):
        response = solicitar(
            client,
            "get",
            "/api/personnel/99",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "http_404"


def test_listar_por_sector_retorna_paginacion():
    client = crear_cliente()

    with (
        patch.object(Sector, "obtener_por_id", return_value=sector()),
        patch.object(Personal, "buscar", return_value=([], 0)) as buscar,
    ):
        response = solicitar(
            client,
            "get",
            "/api/sectors/3/personnel?page=2&per_page=4",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 200
    assert response.json == {
        "data": [],
        "total": 0,
        "page": 2,
        "per_page": 4,
    }
    filtros = buscar.call_args.args[0]
    assert filtros.sector_id == 3
    assert filtros.activo is True
    assert filtros.pagina == 2
    assert filtros.por_pagina == 4


def test_listar_por_sector_rechaza_a_jefe_otro_sector():
    client = crear_cliente()

    with patch.object(Sector, "obtener_por_id") as obtener_sector:
        response = solicitar(
            client,
            "get",
            "/api/sectors/9/personnel",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
        )

    assert response.status_code == 403
    obtener_sector.assert_not_called()


def test_listar_por_sector_inexistente_devuelve_404():
    client = crear_cliente()

    with (
        patch.object(Sector, "obtener_por_id", return_value=None),
        patch.object(Personal, "buscar") as buscar,
    ):
        response = solicitar(
            client,
            "get",
            "/api/sectors/99/personnel",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "http_404"
    buscar.assert_not_called()


def test_crear_residente_por_alimentacion_guarda_sector_null():
    client = crear_cliente()
    residente = persona(tipo_personal_id=2, sector_id=None)

    with (
        patch.object(Personal, "obtener_por_dni", return_value=None),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(2, "Residente"),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "crear_personal", return_value=residente) as crear,
    ):
        response = solicitar(
            client,
            "post",
            "/api/personnel",
            usuario(NombreRol.ALIMENTACION),
            json=datos_personal(tipo_personal_id=2, sector_id=None),
        )

    assert response.status_code == 201
    assert response.json["tipo_personal"]["nombre"] == "Residente"
    assert response.json["sector"] is None
    assert crear.call_args.args[0]["sector_id"] is None


def test_jefe_no_puede_crear_residente():
    client = crear_cliente()

    with (
        patch.object(Personal, "obtener_por_dni", return_value=None),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(2, "Residente"),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "crear_personal") as crear,
    ):
        response = solicitar(
            client,
            "post",
            "/api/personnel",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
            json=datos_personal(tipo_personal_id=2, sector_id=None),
        )

    assert response.status_code == 403
    crear.assert_not_called()


def test_jefe_crea_personal_fijo_asignandolo_a_su_sector():
    client = crear_cliente()
    creado = persona(sector_id=3)

    with (
        patch.object(Personal, "obtener_por_dni", return_value=None),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Sector, "obtener_por_id", return_value=sector()),
        patch.object(Personal, "crear_personal", return_value=creado) as crear,
    ):
        response = solicitar(
            client,
            "post",
            "/api/personnel",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
            json=datos_personal(sector_id=99),
        )

    assert response.status_code == 201
    assert response.json["sector"]["id"] == 3
    assert crear.call_args.args[0]["sector_id"] == 3


def test_crear_personal_con_dni_duplicado_devuelve_409():
    client = crear_cliente()

    with (
        patch.object(Personal, "obtener_por_dni", return_value=persona()),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "crear_personal") as crear,
    ):
        response = solicitar(
            client,
            "post",
            "/api/personnel",
            usuario(NombreRol.ALIMENTACION),
            json=datos_personal(),
        )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "http_409"
    crear.assert_not_called()


def test_modificar_residente_por_alimentacion_fuerza_sector_null():
    client = crear_cliente()
    actual = persona()
    residente = persona(tipo_personal_id=2, sector_id=None)

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            side_effect=[
                tipo_personal(2, "Residente"),
                tipo_personal(),
            ],
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "obtener_por_dni", return_value=actual),
        patch.object(
            Personal,
            "actualizar_personal",
            return_value=residente,
        ) as actualizar,
    ):
        response = solicitar(
            client,
            "put",
            "/api/personnel/7",
            usuario(NombreRol.ALIMENTACION),
            json=datos_personal(tipo_personal_id=2, sector_id=3),
        )

    assert response.status_code == 200
    assert response.json["sector"] is None
    assert actualizar.call_args.args[1]["sector_id"] is None


def test_jefe_no_puede_modificar_residente():
    client = crear_cliente()
    actual = persona()

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            side_effect=[
                tipo_personal(2, "Residente"),
                tipo_personal(),
            ],
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "obtener_por_dni", return_value=actual),
        patch.object(Personal, "actualizar_personal") as actualizar,
    ):
        response = solicitar(
            client,
            "put",
            "/api/personnel/7",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
            json=datos_personal(tipo_personal_id=2, sector_id=None),
        )

    assert response.status_code == 403
    actualizar.assert_not_called()


def test_jefe_no_puede_trasladar_personal_fuera_de_su_sector():
    client = crear_cliente()
    actual = persona(sector_id=3)

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "obtener_por_dni", return_value=actual),
        patch.object(Personal, "actualizar_personal") as actualizar,
    ):
        response = solicitar(
            client,
            "put",
            "/api/personnel/7",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
            json=datos_personal(sector_id=9),
        )

    assert response.status_code == 403
    actualizar.assert_not_called()


def test_modificar_con_dni_duplicado_devuelve_409():
    client = crear_cliente()
    actual = persona(person_id=7)
    otra_persona = persona(person_id=8)

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
        patch.object(TipoMenu, "obtener_por_id", return_value=tipo_menu()),
        patch.object(Personal, "obtener_por_dni", return_value=otra_persona),
        patch.object(Personal, "actualizar_personal") as actualizar,
    ):
        response = solicitar(
            client,
            "put",
            "/api/personnel/7",
            usuario(NombreRol.ALIMENTACION),
            json=datos_personal(),
        )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "http_409"
    actualizar.assert_not_called()


def test_eliminar_por_api_con_historial_desactiva():
    client = crear_cliente()
    actual = persona()

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(Personal, "tiene_historial", return_value=True),
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = solicitar(
            client,
            "delete",
            "/api/personnel/7",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 200
    assert response.json["activo"] is False
    desactivar.assert_called_once_with(7)
    eliminar.assert_not_called()


def test_eliminar_por_api_sin_historial_borra():
    client = crear_cliente()
    actual = persona()

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(Personal, "tiene_historial", return_value=False),
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = solicitar(
            client,
            "delete",
            "/api/personnel/7",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 200
    assert response.json["eliminada"] is True
    eliminar.assert_called_once_with(7)
    desactivar.assert_not_called()


def test_eliminar_por_api_persona_inexistente_devuelve_404():
    client = crear_cliente()

    with patch.object(Personal, "obtener_personal_por_id", return_value=None):
        response = solicitar(
            client,
            "delete",
            "/api/personnel/99",
            usuario(NombreRol.ALIMENTACION),
        )

    assert response.status_code == 404
    assert response.json["error"]["code"] == "http_404"


def test_jefe_no_puede_eliminar_personal_de_otro_sector():
    client = crear_cliente()
    actual = persona(sector_id=9)

    with (
        patch.object(Personal, "obtener_personal_por_id", return_value=actual),
        patch.object(
            TipoPersonal,
            "obtener_por_id",
            return_value=tipo_personal(),
        ),
        patch.object(Personal, "tiene_historial") as historial,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = solicitar(
            client,
            "delete",
            "/api/personnel/7",
            usuario(NombreRol.JEFE_SERVICIO, sector_id=3),
        )

    assert response.status_code == 403
    historial.assert_not_called()
    eliminar.assert_not_called()
