from src.core.db import db
from src.core.usuarios import User
from src.core.permisos import Permiso
from src.core.security import verificar_password


def autenticar_usuario(email: str, password: str) -> tuple[User | None, str | None]:
    """Valida credenciales contra la base de datos sin revelar si falló el email o la contraseña."""
    email_limpio = (email or "").strip().lower()

    if not email_limpio or not password:
        return None, "Debe ingresar su correo electrónico y contraseña."

    usuario = User.obtener_por_email(email_limpio)

    if not usuario or not verificar_password(usuario.password, password):
        return None, "Correo electrónico o contraseña incorrectos."

    if not usuario.activo:
        return None, "Su cuenta se encuentra inactiva. Comuníquese con un administrador."

    return usuario, None


