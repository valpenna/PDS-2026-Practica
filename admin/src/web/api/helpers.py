"""
Decoradores y utilidades para endpoints de la API REST.
"""
from functools import wraps
from flask import request, jsonify, g
import jwt
from enum import Enum
from src.core.tokens import decodificar_token
from src.core.usuarios import User


def token_required(f):
    """
    Valida el header 'Authorization: Bearer <token>'.
    Si el token es válido y el usuario existe y está activo, inyecta el usuario en g.current_user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Falta el token de autorización"}), 401

        partes = auth_header.split()
        if len(partes) != 2 or partes[0].lower() != "bearer":
            return jsonify({"error": "Formato de autorización inválido. Debe ser: Bearer <token>"}), 401

        token = partes[1]

        try:
            payload = decodificar_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return jsonify({"error": "Token inválido"}), 401

            usuario = User.obtener_por_id(int(user_id))
            if not usuario:
                return jsonify({"error": "Usuario no encontrado"}), 401

            # REGLA DE NEGOCIO: Bloquear acceso a usuarios inactivos
            if not usuario.activo:
                return jsonify({"error": "Usuario inactivo o bloqueado"}), 401

            g.current_user = usuario

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "El token ha expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        except Exception:
            return jsonify({"error": "Error al verificar autenticación"}), 401

        return f(*args, **kwargs)

    return decorated


def api_role_required(*allowed_roles):
    """
    Control de acceso para endpoints de la API.
    Acepta instancias de NombreRol o strings.
    
    Ejemplo de uso:
        @api_role_required(NombreRol.JEFE_SERVICIO)
        @api_role_required(NombreRol.ALIMENTACION, NombreRol.COMEDOR)
    """
    roles_permitidos = {
        (r.value if isinstance(r, Enum) else str(r)).lower()
        for r in allowed_roles
    }

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "current_user") or not g.current_user:
                return jsonify({"error": "No autenticado"}), 401

            user_role = g.current_user.rol.nombre if g.current_user.rol else ""
            if user_role.lower() not in roles_permitidos:
                return jsonify({"error": "Acceso denegado: permisos insuficientes para su rol"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator