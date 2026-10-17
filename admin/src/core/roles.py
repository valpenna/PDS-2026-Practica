from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.db import BaseModel,db
from sqlalchemy import select
from enum import Enum

class NombreRol(str, Enum):
    ADMINISTRADOR = "Administrador"
    JEFE_SERVICIO = "Jefe de Servicio"
    ALIMENTACION = "Servicio de Alimentación"
    COMEDOR = "Sector Comedor"

class RolPermiso(BaseModel):
    __tablename__ = "roles_permisos"

    rol_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id"),
        primary_key=True
    )

    permiso_id: Mapped[int] = mapped_column(
        ForeignKey("permisos.id"),
        primary_key=True
    )

    rol: Mapped["Role"] = relationship(
        back_populates="roles_permisos"
    )

    permiso: Mapped["Permiso"] = relationship(
        back_populates="roles_permisos"
    )
    @classmethod
    def obtener_rol_permiso(cls, rol_id, permiso_id):
        consulta = select(cls).where(
            cls.rol_id == rol_id,
            cls.permiso_id == permiso_id
            )
    
        return db.session.scalar(consulta)
    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los roles_permisos ordenados por id."""
        consulta = select(cls).order_by(cls.rol_id,cls.permiso_id)
        return db.session.scalars(consulta).all()


class Role(BaseModel):
    __tablename__ = "roles"

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
        back_populates="rol"
    )
    
    @classmethod
    def obtener_por_nombre(cls, nombre):
        consulta = select(cls).where(cls.nombre == nombre)

        return db.session.scalar(consulta)
    
    @classmethod
    def obtener_por_id(cls, rol_id):
        """Obtiene un rol  por su identificador."""
        return db.session.get(cls, rol_id)
    
    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los roles ordenados por id."""
        consulta = select(cls).order_by(cls.id)
        return db.session.scalars(consulta).all()
    
   