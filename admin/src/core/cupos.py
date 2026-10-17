from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.sectores import Sector
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import db, BaseModel



class SectorCupoInvalido(Exception):
    pass


class CupoDuplicado(Exception):
    pass


@dataclass
class FiltrosCupo:
    por_pagina: int = 25
    sector_id: int | None = None
    tipo_comida: str | None = None
    orden: str | None = None
    pagina: int = 1


class Cupo(BaseModel):
    """Representa el cupo maximo de comensales por sector y tipo de comida."""

    __tablename__ = "cupos"

    __table_args__ = (
        CheckConstraint(
            "cantidad_comensales > 0",
            name="ck_cupos_cantidad_comensales_positiva",
        ),
        CheckConstraint(
            "tipo_comida IN ('desayuno', 'almuerzo', 'merienda', 'cena')",
            name="ck_cupos_tipo_comida_valido",
        ),
        UniqueConstraint(
            "sector_id",
            "tipo_comida",
            name="uq_cupos_sector_tipo_comida",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    sector_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sectores.id"),
        nullable=False,
    )

    sector: Mapped["Sector"] = relationship()

    tipo_comida: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    cantidad_comensales: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los cupos ordenados por identificador."""
        consulta = select(cls).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def buscar(cls, filtros: FiltrosCupo):
        """Busca cupos aplicando condiciones y paginacion."""

        consulta = select(cls)

        consulta = cls._aplicar_filtros(
            consulta,
            filtros
        )

        total = cls._obtener_total(
            consulta
        )

        consulta = cls._aplicar_ordenamiento(
            consulta,
            filtros
        )

        consulta = cls._aplicar_paginacion(
            consulta,
            filtros
        )

        cupos = db.session.scalars(
            consulta
        ).all()

        return cupos, total

    @classmethod
    def _obtener_total(cls, consulta):
        """Obtiene la cantidad total de registros."""
        
        consulta_total = select(func.count()).select_from(
            consulta.subquery()
        )

        return db.session.scalar(
            consulta_total
        ) or 0

    @classmethod
    def _aplicar_filtros(cls, consulta, filtros):
        """Aplica los filtros a la consulta."""
        
        if filtros.sector_id is not None:
            consulta = consulta.where(
                cls.sector_id == filtros.sector_id
            )

        if filtros.tipo_comida:
            consulta = consulta.where(
                cls.tipo_comida == filtros.tipo_comida
            )

        return consulta

    @classmethod
    def _aplicar_ordenamiento(cls, consulta, filtros):
        """Aplica el ordenamiento a la consulta."""
        
        if filtros.orden == "sector":
            consulta = consulta.order_by(
                cls.sector_id,
                cls.id
            )
        else:
            consulta = consulta.order_by(
                cls.id
            )

        return consulta

    @classmethod
    def _aplicar_paginacion(cls, consulta, filtros):
        """Aplica la paginacion a la consulta."""
        
        offset = (
            filtros.pagina - 1
        ) * filtros.por_pagina

        return consulta.offset(
            offset
        ).limit(
            filtros.por_pagina
        )

    @classmethod
    def obtener_por_id(cls, cupo_id):
        """Obtiene un cupo por su identificador."""
        return db.session.get(cls, cupo_id)

    @classmethod
    def obtener_por_sector_y_tipo_comida(cls, sector_id, tipo_comida):
        """Obtiene un cupo por sector y tipo de comida."""
        consulta = select(cls).where(
            cls.sector_id == sector_id,
            cls.tipo_comida == tipo_comida,
        )
        return db.session.scalar(
            consulta
        )

    @classmethod
    def crear(cls, sector_id, tipo_comida, cantidad_comensales):
        cls._validar_asignacion(sector_id, tipo_comida)

        cupo = cls(sector_id=sector_id, tipo_comida=tipo_comida, cantidad_comensales=cantidad_comensales)
        cupo.guardar()
        return cupo

    @classmethod
    def _validar_asignacion(cls, sector_id, tipo_comida, cupo_id=None):
        sector = Sector.obtener_por_id(sector_id)
        if sector is None:
            raise SectorCupoInvalido("El sector indicado no existe.")
        if not sector.activo:
            raise SectorCupoInvalido("No se puede asignar un cupo a un sector inactivo.")
        existente = cls.obtener_por_sector_y_tipo_comida(sector_id, tipo_comida)
        if existente is not None and existente.id != cupo_id:
            raise CupoDuplicado("Ya existe un cupo para ese sector y tipo de comida.")

    def actualizar(self, sector_id, tipo_comida, cantidad_comensales):
        self._validar_asignacion(sector_id, tipo_comida, self.id)
        self.sector_id = sector_id
        self.tipo_comida = tipo_comida
        self.cantidad_comensales = cantidad_comensales
        self.guardar()
        return self

    def guardar(self):
        """Guarda el cupo actual en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def eliminar(self):
        """Elimina el cupo actual de la base de datos."""
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise