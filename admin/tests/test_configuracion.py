import os
import pytest

# Base de datos en memoria para que no dependa de PostgreSQL en CI
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.web import create_app
from src.core.db import db, BaseModel
from src.core.configuracion import Configuracion


@pytest.fixture
def app():
    """Configura una aplicación para testing usando la base de datos en memoria."""
    test_app = create_app(env="testing")

    with test_app.app_context():
        BaseModel.metadata.create_all(db.engine)
        yield test_app
        db.session.close()
        BaseModel.metadata.drop_all(db.engine)


@pytest.fixture
def client(app):
    return app.test_client()


def test_configuracion_valores_por_defecto(app):
    """Verifica que si no existe registro, Configuracion.obtener() crea el valor por defecto."""
    with app.app_context():
        config = Configuracion.obtener()
        assert config.elementos_por_pagina == 25
        assert config.sitio_en_mantenimiento is False
        assert config.mensaje_mantenimiento == "El sitio se encuentra en mantenimiento temporalmente."


def test_actualizar_configuracion_modelo(app):
    """Verifica que el método actualizar guarde los cambios en la base de datos."""
    with app.app_context():
        config = Configuracion.obtener()
        config.actualizar(
            elementos_por_pagina=50,
            sitio_en_mantenimiento=True,
            mensaje_mantenimiento="Sitio cerrado por tareas de actualización."
        )

        actualizada = Configuracion.obtener()
        assert actualizada.elementos_por_pagina == 50
        assert actualizada.sitio_en_mantenimiento is True
        assert actualizada.mensaje_mantenimiento == "Sitio cerrado por tareas de actualización."


def test_vista_configuracion_get(client):
    """Verifica que la pantalla responda con código HTTP 200."""
    response = client.get("/configuracion/")
    assert response.status_code == 200
    assert "Ajustes del Sistema" in response.get_data(as_text=True)


def test_vista_configuracion_post_exitoso(client):
    """Verifica la actualización mediante formulario POST y su redirección (PRG)."""
    response = client.post("/configuracion/actualizar", data={
        "elementos_por_pagina": "30",
        "sitio_en_mantenimiento": "on",
        "mensaje_mantenimiento": "En mantenimiento hasta nuevo aviso"
    }, follow_redirects=True)

    assert response.status_code == 200
    contenido = response.get_data(as_text=True)
    assert "30" in contenido
    assert "En mantenimiento hasta nuevo aviso" in contenido


def test_vista_configuracion_post_invalido(client):
    """Verifica que un valor menor a 1 sea rechazado con mensaje de error."""
    response = client.post("/configuracion/actualizar", data={
        "elementos_por_pagina": "0",
        "mensaje_mantenimiento": ""
    })

    assert response.status_code == 200
    assert "número entero mayor a 0" in response.get_data(as_text=True)