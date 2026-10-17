from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.pedidos import Pedido
from src.core.db import BaseModel, db
from src.core.personal import Personal
from src.core.tipos_menu import TipoMenu


class SolicitudDetalle(BaseModel):
    """Representa un ítem de comida solicitado para una persona."""

    __tablename__ = "solicitudes_detalle"
    __table_args__ = (
        UniqueConstraint(
            "pedido_id",
            "person_id",
            "tipo_comida",
            name="uq_solicitudes_detalle_persona_comida",
        ),
        CheckConstraint(
            "tipo_comida IN ('desayuno', 'almuerzo', 'merienda', 'cena')",
            name="ck_solicitudes_detalle_tipo_comida",
        ),
        CheckConstraint(
            "condicion IN ('regular', 'excepcion')",
            name="ck_solicitudes_detalle_condicion",
        ),
        CheckConstraint(
            "estado_autorizacion IN " "('pendiente', 'autorizado', 'rechazado')",
            name="ck_solicitudes_detalle_estado_autorizacion",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    pedido_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pedidos.id"),
        nullable=False,
    )
    pedido = relationship("Pedido", back_populates="detalles")

    person_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("personal.id"),
        nullable=False,
    )
    persona: Mapped["Personal"] = relationship("Personal")

    person_dni_snapshot: Mapped[str] = mapped_column(String(12), nullable=False)
    person_nombre_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    person_apellido_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_personal_id_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sector_id_snapshot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activo_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False)

    tipo_comida: Mapped[str] = mapped_column(String(20), nullable=False)

    tipo_menu_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tipos_menu.id"),
        nullable=False,
    )
    tipo_menu: Mapped["TipoMenu"] = relationship("TipoMenu")

    condicion: Mapped[str] = mapped_column(String(20), nullable=False)

    estado_autorizacion: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pendiente'"),
    )

    validado_por_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id"),
        nullable=True,
    )
    validado_por = relationship("User")

    fecha_validacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @classmethod
    def participo_en_validaciones(cls, user_id: int) -> bool:
        """Indica si el usuario valido alguna solicitud."""
        consulta = select(cls.id).where(cls.validado_por_id == user_id).limit(1)
        return db.session.scalar(consulta) is not None

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los detalles ordenados por id."""
        consulta = select(cls).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_por_id(cls, solicitud_detalle_id: int):
        """Obtiene un detalle por su id."""
        return db.session.get(cls, solicitud_detalle_id)

    @classmethod
    def obtener_por_pedido(cls, pedido_id: int):
        """Obtiene los detalles asociados a un pedido."""
        consulta = select(cls).where(cls.pedido_id == pedido_id).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_por_persona(cls, person_id: int):
        """Obtiene los detalles de pedidos asociados a una persona."""
        consulta = select(cls).where(cls.person_id == person_id).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def existe_por_persona(cls, person_id: int) -> bool:
        """Indica si una persona aparece en algún detalle de pedido."""
        consulta = select(cls.id).where(cls.person_id == person_id).limit(1)
        return db.session.scalar(consulta) is not None

    @classmethod
    def eliminar_por_pedido(cls, pedido_id):
        """Elimina todas las solicitudes detalle asociadas a un pedido."""
        detalles = db.session.scalars(
            select(cls).where(cls.pedido_id == pedido_id)
        ).all()

        for detalle in detalles:
            db.session.delete(detalle)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def crear(cls, datos: dict):
        """Crea y persiste un detalle de solicitud."""
        solicitud_detalle = cls(**datos)
        db.session.add(solicitud_detalle)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return solicitud_detalle

    @classmethod
    def actualizar(cls, solicitud_detalle_id: int, datos: dict):
        """Actualiza un detalle existente y devuelve None si no existe."""
        solicitud_detalle = cls.obtener_por_id(solicitud_detalle_id)
        if solicitud_detalle is None:
            return None

        for campo, valor in datos.items():
            setattr(solicitud_detalle, campo, valor)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return solicitud_detalle
    
    @classmethod
    def obtener_autorizada_para_entrega(
        cls,
        person_id,
        tipo_comida,
        fecha
    ):
        consulta = (
            select(cls)
            .join(Pedido, Pedido.id == cls.pedido_id)
            .where(
                cls.person_id == person_id,
                cls.tipo_comida == tipo_comida,
                Pedido.fecha == fecha,
                cls.estado_autorizacion == "autorizado"
            )
        )

        return db.session.scalar(consulta)
    @classmethod
    def eliminar(cls, solicitud_detalle_id: int) -> bool:
        """Elimina un detalle y devuelve si se encontró."""
        solicitud_detalle = cls.obtener_por_id(solicitud_detalle_id)
        if solicitud_detalle is None:
            return False

        db.session.delete(solicitud_detalle)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return True

    def guardar(self):
        """Guarda el detalle actual en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
