from src.core.db import (
    db,
    BaseModel,
)  # importo la base de datos y la clase BaseModel para que los modelos hereden de ella
from sqlalchemy import BigInteger, String, select
from sqlalchemy.orm import Mapped, mapped_column

class TipoPersonal(BaseModel): 
    """Catálogo de tipos de personal disponibles en el sistema."""

    __tablename__ = "tipos_personal"

    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True
    )

    nombre: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los tipos de personal."""
        return db.session.scalars(select(cls).order_by(cls.id)).all()

    @classmethod
    def obtener_por_id(cls, tipo_personal_id: int):
        """Obtiene un tipo de personal por su identificador."""
        return db.session.get(cls, tipo_personal_id)

    @classmethod
    def obtener_por_nombre(cls, nombre: str):
        """Obtiene un tipo de personal por su nombre."""
        return db.session.query(cls).filter_by(nombre=nombre).first()
