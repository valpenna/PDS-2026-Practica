from functools import wraps
from flask import abort, flash, redirect, session, url_for
from enum import Enum
from src.core.usuarios import User

def is_authenticated() -> bool:
    """Verifica si existe un usuario con sesión activa en el servidor."""
    return "user_id" in session


def current_user_id() -> int | None:
    """Retorna el identificador del usuario autenticado o None."""
    return session.get("user_id")


def login_required(view_func):
    """
    Decorador que restringe el acceso a vistas privadas.
    Si el usuario no está autenticado, redirige al formulario de login con un mensaje flash.
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not is_authenticated():
            flash("Debe iniciar sesión para acceder a esta sección.", "warning")
            return redirect(url_for("auth.login_get"))
        return view_func(*args, **kwargs)

    return decorated_view


def has_permission(permission_name: str) -> bool:
    """Verifica si el usuario autenticado posee el permiso indicado."""
    user_id = session.get("user_id")
    if not user_id:
        return False
    return User.tiene_permiso(user_id, permission_name)


def check_permission(permission_name: str):
    """
    Decorador que valida que el usuario esté autenticado y cuente
    con el permiso atómico indicado. Si no lo tiene, responde 403 Forbidden.
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not is_authenticated():
                flash("Debe iniciar sesión para acceder a esta sección.", "warning")
                return redirect(url_for("auth.login_get"))

            if not has_permission(permission_name):
                abort(403)

            return view_func(*args, **kwargs)

        return decorated_view

    return decorator


def role_required(*allowed_roles):
    """
    Decorador que restringe el acceso a uno o más roles específicos.
    Acepta strings o instancias del Enum NombreRol.
    
    Ejemplo:
        @role_required(NombreRol.ADMINISTRADOR)
        @role_required(NombreRol.ADMINISTRADOR, NombreRol.JEFE_SERVICIO)
        @role_required("Administrador", "Sector Comedor")
    """
    # Normalizamos los roles a strings en minúsculas para comparar de forma segura
    roles_permitidos = {
        (r.value if isinstance(r, Enum) else str(r)).lower()
        for r in allowed_roles
    }

    def decorator(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not is_authenticated():
                flash("Debe iniciar sesión para acceder a esta sección.", "warning")
                return redirect(url_for("auth.login_get"))

            user_role = session.get("user_role", "")
            if user_role.lower() not in roles_permitidos:
                abort(403)

            return view_func(*args, **kwargs)

        return decorated_view

    return decorator


