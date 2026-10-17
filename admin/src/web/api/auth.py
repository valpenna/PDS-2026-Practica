"""
Endpoints de la API de Autenticación.
"""
from flask import Blueprint, request, jsonify, g
from src.core.auth import autenticar_usuario
from src.core.tokens import generar_token
from src.web.api.helpers import token_required

auth_api_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_api_bp.post("/login")
def login():
    """
    POST /api/auth/login
    Inicia sesión con email y contraseña, retornando token JWT y datos de perfil.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "El cuerpo de la petición debe ser un JSON válido"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Debe ingresar correo electrónico y contraseña"}), 400

    # Usamos la lógica de negocio ya testeada en src/core/auth.py
    usuario, error = autenticar_usuario(email, password)
    if error:
        # 401 tanto para credenciales incorrectas como para cuenta inactiva
        return jsonify({"error": error}), 401

    token = generar_token(usuario.id)

    return jsonify({
        "token": token,
        "user": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "email": usuario.email,
            "rol": usuario.rol.nombre if usuario.rol else None,
            "sector_id": usuario.sector_id
        }
    }), 200


@auth_api_bp.get("/me")
@token_required
def me():
    """
    GET /api/auth/me
    Retorna la información del usuario autenticado a partir del Bearer token.
    """
    usuario = g.current_user
    return jsonify({
        "id": usuario.id,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "email": usuario.email,
        "rol": usuario.rol.nombre if usuario.rol else None,
        "sector_id": usuario.sector_id
    }), 200


@auth_api_bp.post("/logout")
@token_required
def logout():
    """
    POST /api/auth/logout
    Cierre de sesión para la API stateless.
    """
    return jsonify({"message": "Sesión cerrada correctamente"}), 200