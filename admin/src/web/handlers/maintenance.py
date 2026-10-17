from flask import render_template, request, session
from src.core.configuracion import Configuracion
from src.core.roles import NombreRol
from src.web.helpers.auth import is_authenticated


def check_maintenance():
    """Verifica si el sistema se encuentra en modo mantenimiento y restringe el acceso."""
    # 1. Archivos estáticos siempre disponibles
    if request.endpoint and request.endpoint.startswith("static"):
        return None

    # 2. Rutas de autenticación para permitir login/logout
    if request.path.startswith("/auth"):
        return None

    # 3. Si el usuario está autenticado y su rol es Administrador, tiene acceso irrestricto
    if is_authenticated():
        rol_usuario = str(session.get("user_role", "")).strip().lower()
        rol_admin = NombreRol.ADMINISTRADOR.value.lower()
        if rol_usuario == rol_admin:
            return None

    # 4. Excepción de seguridad para la URL de configuración
    if request.path.startswith("/configuracion"):
        return None

    # 5. Para el resto de usuarios o no autenticados, si está activo el mantenimiento, 503
    config_sistema = Configuracion.obtener()
    if config_sistema.sitio_en_mantenimiento:
        mensaje = (
            config_sistema.mensaje_mantenimiento
            or "El sistema se encuentra en mantenimiento temporal."
        )
        return render_template("configuracion/mantenimiento.html", mensaje=mensaje), 503

    return None