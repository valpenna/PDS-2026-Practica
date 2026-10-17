from dataclasses import dataclass

from src.core.db import BaseModel, db
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    and_,
    func,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


@dataclass
class FiltrosPedido:
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    sector_id: int | None = None
    tipo_comida: str | None = None
    tipo_menu_id: int | None = None
    estado: str | None = None
    pagina: int = 1
    por_pagina: int = 25


class PedidoYaResuelto(Exception):
    pass


class SolicitudesInvalidas(Exception):
    pass


class Pedido(BaseModel):
    """Representa un pedido de viandas realizado por un sector."""

    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint(
            "sector_id",
            "fecha",
            name="uq_pedidos_sector_fecha",
        ),
        CheckConstraint(
            "estado IN ('confirmado', 'autorizado', 'rechazado')",
            name="ck_pedidos_estado",
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
    sector = relationship("Sector")
    detalles = relationship(
        "SolicitudDetalle",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'confirmado'"),
    )

    created_by_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    creado_por = relationship("User")

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los pedidos ordenados por fecha e identificador."""
        consulta = select(cls).order_by(cls.fecha.desc(), cls.id.desc())
        return db.session.scalars(consulta).all()

    @classmethod
    def buscar(cls, filtros: FiltrosPedido):
        """Busca pedidos filtrados y paginados, y devuelve su total."""
        from src.core.solicitudes_detalle import SolicitudDetalle

        consulta = select(cls)
        if filtros.fecha_desde is not None:
            consulta = consulta.where(cls.fecha >= filtros.fecha_desde)
        if filtros.fecha_hasta is not None:
            consulta = consulta.where(cls.fecha <= filtros.fecha_hasta)
        if filtros.sector_id is not None:
            consulta = consulta.where(cls.sector_id == filtros.sector_id)
        if filtros.estado is not None:
            consulta = consulta.where(cls.estado == filtros.estado)
        else:
            consulta = consulta.where(cls.estado.in_(("confirmado", "autorizado")))

        condiciones_detalle = []
        if filtros.tipo_comida is not None:
            condiciones_detalle.append(SolicitudDetalle.tipo_comida == filtros.tipo_comida)
        if filtros.tipo_menu_id is not None:
            condiciones_detalle.append(SolicitudDetalle.tipo_menu_id == filtros.tipo_menu_id)
        if condiciones_detalle:
            consulta = consulta.where(cls.detalles.any(and_(*condiciones_detalle)))

        total = db.session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        pedidos = db.session.scalars(
            consulta.order_by(cls.fecha.desc(), cls.id.desc())
            .offset((filtros.pagina - 1) * filtros.por_pagina)
            .limit(filtros.por_pagina)
        ).all()
        return pedidos, total

    @classmethod
    def obtener_por_id(cls, pedido_id: int):
        """Obtiene un pedido por su identificador."""
        return db.session.get(cls, pedido_id)

    @classmethod
    def autorizar(cls, pedido_id: int, autorizaciones: list[dict], validador_id: int):
        """Resuelve todas las solicitudes nominadas de un pedido en una transaccion."""
        from src.core.solicitudes_detalle import SolicitudDetalle

        pedido = db.session.scalar(select(cls).where(cls.id == pedido_id).with_for_update())
        if pedido is None:
            return None
        if pedido.estado != "confirmado":
            raise PedidoYaResuelto("El pedido ya fue autorizado o rechazado.")

        solicitudes = SolicitudDetalle.obtener_por_pedido(pedido_id)
        solicitudes_por_id = {solicitud.id: solicitud for solicitud in solicitudes}
        cls._validar_autorizaciones(solicitudes_por_id, autorizaciones)

        fecha_validacion = datetime.now(timezone.utc)
        for autorizacion in autorizaciones:
            solicitud = solicitudes_por_id[autorizacion["id"]]
            solicitud.estado_autorizacion = "autorizado" if autorizacion["autorizada"] else "rechazado"
            solicitud.validado_por_id = validador_id
            solicitud.fecha_validacion = fecha_validacion

        pedido.estado = "autorizado" if any(autorizacion["autorizada"] for autorizacion in autorizaciones) else "rechazado"
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return pedido

    @staticmethod
    def _validar_autorizaciones(solicitudes_por_id: dict, autorizaciones: list[dict]) -> None:
        ids = [autorizacion["id"] for autorizacion in autorizaciones]
        if (not solicitudes_por_id or len(ids) != len(solicitudes_por_id)
                or set(ids) != solicitudes_por_id.keys()):
            raise SolicitudesInvalidas("Las decisiones deben incluir exactamente las solicitudes del pedido, sin repetir.")

    @classmethod
    def obtener_por_sector(cls, sector_id: int):
        """Obtiene los pedidos de un sector."""
        consulta = (
            select(cls)
            .where(cls.sector_id == sector_id)
            .order_by(cls.fecha.desc(), cls.id.desc())
        )
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_por_creador(cls, creador_id: int):
        """Obtiene los pedidos de un creador."""
        consulta = (
            select(cls)
            .where(cls.created_by_id == creador_id)
            .order_by(cls.fecha.desc(), cls.id.desc())
        )
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_por_sector_y_fecha(cls, sector_id, fecha):
        """Obtiene un pedido por sector y fecha."""
        consulta = select(cls).where(cls.sector_id == sector_id, cls.fecha == fecha)

        return db.session.scalar(consulta)

    @classmethod
    def crear(cls, datos: dict):
        """Crea y persiste un pedido."""
        pedido = cls(**datos)
        db.session.add(pedido)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return pedido

    @classmethod
    def actualizar(cls, pedido_id: int, datos: dict):
        """Actualiza un pedido y devuelve None si no existe."""
        pedido = cls.obtener_por_id(pedido_id)
        if pedido is None:
            return None

        for campo, valor in datos.items():
            setattr(pedido, campo, valor)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return pedido

    @classmethod
    def eliminar(cls, pedido_id: int) -> bool:
        """Elimina un pedido confirmado y sus detalles si se encontró."""
        pedido = cls.obtener_por_id(pedido_id)
        if pedido is None:
            return False

        if pedido.estado != "confirmado":
            raise ValueError("Solo se pueden eliminar pedidos en estado confirmado.")

        db.session.delete(pedido)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return True

    def guardar(self):
        """Guarda el pedido actual en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
