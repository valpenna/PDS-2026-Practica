from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

import src.web
from src.core.personal import Personal
from src.core.usuarios import User
from src.web.controllers.personal import personal_bp


def crear_cliente():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(personal_bp)

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_role"] = "Administrador"

    return client


def test_eliminar_personal_con_historial_lo_desactiva():
    client = crear_cliente()
    persona = SimpleNamespace(activo=True)

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch.object(Personal, "obtener_personal_por_id", return_value=persona),
        patch.object(Personal, "tiene_historial", return_value=True),
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = client.post("/personal/eliminar/7")

    assert response.status_code == 302
    desactivar.assert_called_once_with(7)
    eliminar.assert_not_called()


def test_eliminar_personal_sin_historial_lo_borra():
    client = crear_cliente()
    persona = SimpleNamespace(activo=True)

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch.object(Personal, "obtener_personal_por_id", return_value=persona),
        patch.object(Personal, "tiene_historial", return_value=False),
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = client.post("/personal/eliminar/7")

    assert response.status_code == 302
    eliminar.assert_called_once_with(7)
    desactivar.assert_not_called()


def test_eliminar_personal_inexistente_no_consulta_historial():
    client = crear_cliente()

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch.object(Personal, "obtener_personal_por_id", return_value=None),
        patch.object(Personal, "tiene_historial") as historial,
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = client.post("/personal/eliminar/7")

    assert response.status_code == 302
    historial.assert_not_called()
    desactivar.assert_not_called()
    eliminar.assert_not_called()


def test_eliminar_personal_ya_inactivo_no_lo_procesa():
    client = crear_cliente()
    persona = SimpleNamespace(activo=False)

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch.object(Personal, "obtener_personal_por_id", return_value=persona),
        patch.object(Personal, "tiene_historial") as historial,
        patch.object(Personal, "marcar_como_inactivo") as desactivar,
        patch.object(Personal, "eliminar_personal") as eliminar,
    ):
        response = client.post("/personal/eliminar/7")

    assert response.status_code == 302
    historial.assert_not_called()
    desactivar.assert_not_called()
    eliminar.assert_not_called()
