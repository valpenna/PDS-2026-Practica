"""
Módulo para generación y validación de tokens JWT.
"""
from datetime import datetime, timezone, timedelta
import jwt
from flask import current_app


def generar_token(user_id: int, horas_validez: int = 24) -> str:
    """
    Genera un token JWT firmado con el ID del usuario como string.
    """
    secret_key = current_app.config.get("SECRET_KEY")
    ahora = datetime.now(timezone.utc)
    
    payload = {
        "sub": str(user_id),  # RFC 7519 exige que sub sea string
        "iat": ahora,
        "exp": ahora + timedelta(hours=horas_validez)
    }
    
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    """
    Decodifica y verifica la firma y expiración del token con SECRET_KEY.
    """
    secret_key = current_app.config.get("SECRET_KEY")
    return jwt.decode(token, secret_key, algorithms=["HS256"])