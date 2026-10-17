from dataclasses import dataclass
from flask import render_template

@dataclass
class HTTPError:
    code: int
    message: str
    description: str

def not_found(e):
    error = HTTPError (
        code=404,
        message="No encontrado",
        description="La página que buscas no existe."
    )
    return render_template('error.html', error=error), 404

def unauthorized(e):
    error = HTTPError (
        code=401,
        message="No autorizado",
        description="No tenés permiso para acceder a este recurso."
    )
    return render_template('error.html', error=error), 401

def internal_server_error(e):
    error = HTTPError (
        code=500,
        message="Error interno del servidor",
        description="Ocurrió un problema inesperado. Intentalo nuevamente más tarde."
    )
    return render_template('error.html', error=error), 500


def forbidden(e):
    error = HTTPError(
        code=403,
        message="Acceso Prohibido",
        description="No posee los permisos necesarios para realizar esta acción."
    )
    return render_template("error.html", error=error), 403