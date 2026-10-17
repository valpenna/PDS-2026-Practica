from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.db import BaseModel,db
from sqlalchemy import select
from enum import Enum

class NombrePermiso(str, Enum):
    USER_INDEX = "user_index"
    USER_NEW = "user_new"
    USER_UPDATE = "user_update"
    USER_DESTROY = "user_destroy"
    USER_SHOW = "user_show"

    SECTOR_INDEX = "sector_index"
    SECTOR_NEW = "sector_new"
    SECTOR_UPDATE = "sector_update"
    SECTOR_DESTROY = "sector_destroy"
    SECTOR_SHOW = "sector_show"

    PERSONAL_INDEX = "personal_index"
    PERSONAL_NEW = "personal_new"
    PERSONAL_UPDATE = "personal_update"
    PERSONAL_DESTROY = "personal_destroy"
    PERSONAL_SHOW = "personal_show"
    PERSONAL_IMPORT = "personal_import"
    
class Permiso(BaseModel):
    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    roles_permisos: Mapped[list["RolPermiso"]] = relationship(
        back_populates="permiso"
    )
    @classmethod
    def obtener_por_nombre(cls, nombre):
        consulta = select(cls).where(cls.nombre == nombre)
        return db.session.scalar(consulta)