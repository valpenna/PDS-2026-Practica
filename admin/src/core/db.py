from flask_sqlalchemy_lite import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

db = SQLAlchemy()


def init_app(app):
    db.init_app(app)
    return db


class BaseModel(DeclarativeBase):
    """Base model class for all models."""
    __abstract__ = True


def create_tables():
    from src.core.usuarios import User  # noqa: F401
    from src.core.sectores import Sector  # noqa: F401
    from src.core.permisos import Permiso  # noqa: F401
    from src.core.roles import Role, RolPermiso  # noqa: F401
    from src.core.tipos_menu import TipoMenu  # noqa: F401
    from src.core.tipos_personal import TipoPersonal  # noqa: F401
    from src.core.personal import Personal  # noqa: F401
    from src.core.pedidos import Pedido  # noqa: F401
    from src.core.solicitudes_detalle import SolicitudDetalle
    from src.core.entregas import Entrega, EntregaDetalle  # noqa: F401
    from src.core.cupos import Cupo  # noqa: F401
    from src.core import seeds
    #from src.core import seeds_test as seeds TESTEO_RESUMENES_API_SEED
    BaseModel.metadata.create_all(db.engine)
    seeds.run()


def reset_db():
    from src.core.roles import Role, RolPermiso  # noqa: F401
    from src.core.usuarios import User  # noqa: F401
    from src.core.permisos import Permiso  # noqa: F401
    from src.core.sectores import Sector  # noqa: F401
    from src.core.personal import Personal  # noqa: F401
    from src.core.tipos_menu import TipoMenu  # noqa: F401
    from src.core.tipos_personal import TipoPersonal  # noqa: F401
    from src.core.pedidos import Pedido  # noqa: F401
    from src.core.entregas import Entrega, EntregaDetalle  # noqa: F401
    from src.core.solicitudes_detalle import SolicitudDetalle  # noqa: F401
    from src.core.cupos import Cupo  # noqa: F401

    BaseModel.metadata.drop_all(db.engine)
    BaseModel.metadata.create_all(db.engine)
