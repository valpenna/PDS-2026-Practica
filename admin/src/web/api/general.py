from functools import wraps

from flask import Blueprint, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from src.core.roles import NombreRol
from src.core.configuracion import Configuracion
from src.core.usuarios import User
from src.core.tipos_menu import TipoMenu
from src.core.tipos_personal import TipoPersonal
from types import SimpleNamespace
from src.web.api.helpers import token_required

general_api_bp = Blueprint("api_general", __name__, url_prefix="/api")


# En el futuro, reemplazar esta verificación de sesión por autenticación con token Bearer.
def _sesion_requerida(view_func):
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        user_id = session.get("user_id")
        usuario = User.obtener_por_id(user_id) if isinstance(user_id, int) else None

        if usuario is None or not usuario.activo:
            session.clear()
            abort(401, description="Se requiere una sesión válida.")

        g.api_user = usuario
        return view_func(*args, **kwargs)

    return decorated_view


@general_api_bp.errorhandler(HTTPException)
def _error_http_api(error):
    return (
        jsonify(
            error={
                "status": error.code,
                "detail": error.description,
            }
        ),
        error.code,
    )


@general_api_bp.get("/menu-types")
@token_required
def listar_menus():
    """
    Proposito: Listar menus para todos los roles
    Entrada: -
    Salida: JSON con listado de menus
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar tipos de menu."}),
            403,
        )

    tipos_menu = TipoMenu.obtener_todos()
    return (
        jsonify(
            [
                {
                    "id": menu.id,
                    "nombre": menu.nombre,
                }
                for menu in tipos_menu
            ]
        ),
        200,
    )


@general_api_bp.get("/personnel-types")
@token_required
def listar_tipos_personal():
    """
    Proposito: Listar menus para todos los roles
    Entrada: -
    Salida: JSON con listado de tipos de personal
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify(
                {"error": "El rol del usuario no puede consultar tipos de personal."}
            ),
            403,
        )
    tipos_personal = TipoPersonal.obtener_todos()
    return (
        jsonify(
            [
                {
                    "id": personal.id,
                    "nombre": personal.nombre,
                }
                for personal in tipos_personal
            ]
        ),
        200,
    )


@general_api_bp.get("/configuration")
@token_required
def obtener_configuracion():
    """Muestra la configuracion actual del sistema"""
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify(
                {
                    "error": "El rol del usuario no puede consultar la configuracion del sistema."
                }
            ),
            403,
        )
    config = Configuracion.obtener()

    return (
        jsonify(
            {
                "elementos_por_pagina": config.elementos_por_pagina,
                "sitio_en_mantenimiento": config.sitio_en_mantenimiento,
                "mensaje_mantenimiento": config.mensaje_mantenimiento,
            }
        ),
        200,
    )
