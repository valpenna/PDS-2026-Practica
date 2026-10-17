# Grupo 25 - Proyecto de Software 2026

### 📚 Descripción

Este repositorio contiene las actividades desarrolladas durante la materia **Proyecto de Software**.

### 🛠️ Herramientas y tecnologías

- **Flask**: framework web utilizado para desarrollar la aplicación privada de administración. Se utiliza para definir las rutas, recibir las solicitudes HTTP y renderizar las vistas de la aplicación.

- **SQLAlchemy**: ORM utilizado para interactuar con la base de datos mediante modelos y consultas en Python, evitando trabajar directamente con consultas SQL en la aplicación.

- **Flask-SQLAlchemy Lite**: extensión que integra SQLAlchemy con Flask y simplifica la configuración y el manejo de las sesiones de base de datos dentro de la aplicación.

- **Pydantic**: utilizado para validar los datos recibidos por el backend. Permite definir tipos, restricciones y reglas de validación antes de utilizar los datos en la aplicación o almacenarlos en la base de datos.

- **Pytest**: framework utilizado para implementar y ejecutar las pruebas automatizadas del proyecto, permitiendo verificar el comportamiento de las distintas funcionalidades.

- **Poetry**: herramienta utilizada para administrar las dependencias y el entorno del proyecto, manteniendo las versiones definidas en `pyproject.toml` y `poetry.lock`.

### 👥 Integrantes

* Nahuel Condisciani - [@nahuelcondisciani](https://gitlab.catedras.linti.unlp.edu.ar)
* Nicolas Mele - [@nico.mele](https://gitlab.catedras.linti.unlp.edu.ar)
* Thiago Martinez - [@thiagomartinez](https://gitlab.catedras.linti.unlp.edu.ar)
* Luca Roman - [@rl.romanluca](https://gitlab.catedras.linti.unlp.edu.ar)
* Valentina Pennacchioni - [@valentinapennacchioni](https://gitlab.catedras.linti.unlp.edu.ar)

### 📌 Inicio Rápido - Panel de Administración

```bash
cd admin
poetry install
poetry run flask --app src.web run --debug