from types import SimpleNamespace
from dotenv import load_dotenv
from flask import Flask, render_template, session
from flask_session import Session

from .config import config
from src.core.db import db, create_tables, reset_db
from src.core.configuracion import Configuracion
from src.web.helpers.statistics import obtener_estadisticas_usuarios, obtener_estadisticas_sectores, obtener_estadisticas_personal

# Handlers de error
from src.web.handlers.error import (
    internal_server_error,
    not_found,
    unauthorized,
    forbidden,
)
from src.web.handlers.maintenance import check_maintenance

# Blueprints
from src.web.controllers.auth import auth_bp
from src.web.controllers.configuracion import configuracion_bp
from src.web.controllers.sectores import sectores_bp
from src.web.controllers.usuarios import usuarios_bp
from src.web.api.sectores import sectores_api_bp
from src.web.api.general import general_api_bp
from src.web.api.entregas import authorized_meals_api_bp, entregas_api_bp
from src.web.api.cupos import cupos_api_bp
from src.web.api.autorizaciones import autorizaciones_api_bp
from src.web.api.auth import auth_api_bp
from src.web.controllers.personal import personal_bp
from src.web.api.pedidos import pedidos_api_bp
from src.web.api.personal import personal_api_bp, personal_sector_api_bp

from src.web.api.summaries import summaries_api_bp
# Helpers de autenticación
from src.web.helpers.auth import is_authenticated, has_permission, login_required


def create_app(env="development", static_folder="../../static"):
    load_dotenv()

    app = Flask(__name__, static_folder=static_folder)
    app.config.from_object(config[env])
    Session(app)

    db.init_app(app)

    # Inicialización de tablas, seeds y configuración en un solo paso
    with app.app_context():
        create_tables()
        Configuracion.obtener()

    # Comando CLI para resetear la base de datos
    @app.cli.command("reset-db")
    def reset_db_command():
        reset_db()
        Configuracion.obtener()
        print("Base de datos reiniciada e inicializada correctamente.")

    # Middleware de mantenimiento
    app.before_request(check_maintenance)

    # Inyección de helpers 
    @app.context_processor
    def inject_auth_helpers():
        def get_current_user():
            if not is_authenticated():
                return None
            return SimpleNamespace(
                id=session.get("user_id"),
                email=session.get("user_email"),
                nombre=session.get("user_nombre", "").split()[0] if session.get("user_nombre") else "",
                apellido=session.get("user_nombre", "").split()[-1] if session.get("user_nombre") else "",
                rol=session.get("user_role"),
                sector_id=session.get("sector_id"),
            )

        return {
            "current_user": get_current_user(),
            "is_authenticated": is_authenticated,
            "has_permission": has_permission,
        }

    @app.route("/")
    @login_required
    def home():
        return render_template(
            "home.html",
            active_page="home",
            user_stats=obtener_estadisticas_usuarios(),
            sector_stats=obtener_estadisticas_sectores(),
            personal_stats=obtener_estadisticas_personal(),
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(sectores_bp)
    app.register_blueprint(personal_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(sectores_api_bp)
    app.register_blueprint(general_api_bp)
    app.register_blueprint(authorized_meals_api_bp)
    app.register_blueprint(entregas_api_bp)
    app.register_blueprint(pedidos_api_bp)
    app.register_blueprint(auth_api_bp)
    app.register_blueprint(personal_api_bp)
    app.register_blueprint(personal_sector_api_bp)
    app.register_blueprint(autorizaciones_api_bp)
    app.register_blueprint(summaries_api_bp)
    # Handlers de errores
    app.register_blueprint(cupos_api_bp)
    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)
    app.register_error_handler(404, not_found)
    app.register_error_handler(500, internal_server_error)

    return app