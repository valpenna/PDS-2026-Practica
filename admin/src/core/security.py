from werkzeug.security import generate_password_hash, check_password_hash

def hashear_password(password):
    """Genera un hash seguro para una contraseña."""
    return generate_password_hash(password)


def verificar_password(password_hash, password):
    """Verifica una contraseña contra su hash."""
    return check_password_hash(password_hash, password)