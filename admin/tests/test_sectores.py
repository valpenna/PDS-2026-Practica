from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flask import Flask

import src.web
from src.core.personal import Personal
from src.core.pedidos import Pedido
from src.core.sectores import Sector
from src.core.usuarios import User
from src.web.controllers.sectores import sectores_bp


@pytest.mark.parametrize(
    ("tiene_usuarios", "tiene_personal", "tiene_pedidos", "detalle"),
    [
        (False, False, False, None),
        (True, False, False, "usuarios"),
        (False, True, False, "personal"),
        (False, False, True, "pedidos"),
        (True, True, False, "usuarios y personal"),
        (True, False, True, "usuarios y pedidos"),
        (False, True, True, "personal y pedidos"),
        (True, True, True, "usuarios, personal y pedidos"),
    ],
)
def test_eliminar_sector_desactiva_y_detalla_asociaciones(
    tiene_usuarios, tiene_personal, tiene_pedidos, detalle
):
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(sectores_bp)
    sector = SimpleNamespace(activo=True, guardar=Mock())

    with (
        patch.object(User, "tiene_permiso", return_value=True),
        patch.object(Sector, "obtener_por_id", return_value=sector),
        patch.object(User, "obtener_por_sector", return_value=[object()] if tiene_usuarios else []),
        patch.object(
            Personal,
            "obtener_por_sector",
            return_value=object() if tiene_personal else None,
        ),
        patch.object(
            Pedido,
            "obtener_por_sector",
            return_value=[object()] if tiene_pedidos else [],
        ),
        patch.object(Sector, "eliminar_sector") as eliminar_sector,
    ):
        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 1
            session["user_role"] = "Administrador"

        response = client.get("/sectores/eliminar/1")

        assert response.status_code == 302
        if detalle:
            assert sector.activo is False
            sector.guardar.assert_called_once()
            eliminar_sector.assert_not_called()
            with client.session_transaction() as session:
                mensaje = session["_flashes"][0][1]
            assert detalle in mensaje
            assert "El sector fue desactivado." in mensaje
        else:
            assert sector.activo is True
            sector.guardar.assert_not_called()
            eliminar_sector.assert_called_once_with(1)
