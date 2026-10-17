from sqlalchemy import BigInteger, Boolean, Integer, Text, select
from sqlalchemy.orm import Mapped, mapped_column
from src.core.db import db, BaseModel


class Configuracion(BaseModel):
    """Representa los ajustes y parámetros globales del sistema."""

    __tablename__ = "configuraciones"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    elementos_por_pagina: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25
    )

    sitio_en_mantenimiento: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    mensaje_mantenimiento: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    @classmethod
    def obtener(cls):
        """Obtiene la configuración global del sistema o crea la inicial si no existe."""
        consulta = select(cls).limit(1)
        config = db.session.scalar(consulta)

        if not config:
            config = cls(
                elementos_por_pagina=25,
                sitio_en_mantenimiento=False,
                mensaje_mantenimiento="El sitio se encuentra en mantenimiento temporalmente."
            )
            config.guardar()

        return config

    def actualizar(self, elementos_por_pagina: int, sitio_en_mantenimiento: bool, mensaje_mantenimiento: str | None = None):
        """Actualiza los valores de configuración."""
        self.elementos_por_pagina = elementos_por_pagina
        self.sitio_en_mantenimiento = sitio_en_mantenimiento
        self.mensaje_mantenimiento = mensaje_mantenimiento
        self.guardar()

    def guardar(self):
        """Persiste la configuración en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise