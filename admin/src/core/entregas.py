from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, select, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.db import db, BaseModel
from src.core.tipos_menu import TipoMenu
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.pedidos import Pedido
from src.web.helpers.paginator import paginate_query


class EntregaDetalle(BaseModel):
    """Representa detalladamente una entrega del sistema."""

    __tablename__ = "entregas_detalle"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    entrega_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("entregas.id"),
        nullable=False
    )

    entrega: Mapped["Entrega"] = relationship(
        back_populates="detalles"
    )

    solicitud_detalle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("solicitudes_detalle.id"),
        nullable=False,
        unique=True
    )

    solicitud_detalle: Mapped["SolicitudDetalle"] = relationship()

    tipo_menu_entregado_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tipos_menu.id"),
        nullable=False
    )

    tipo_menu_entregado: Mapped["TipoMenu"] = relationship(
        "TipoMenu"
    )

    def guardar(self):
        """Guarda el detalle de una entrega."""
        db.session.add(self)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def obtener_por_id(cls, detalle_id):
        """Obtiene un detalle de entrega por ID."""
        return db.session.get(cls, detalle_id)

    @classmethod
    def obtener_por_entrega(cls, entrega_id):
        """Obtiene todos los detalles correspondientes a una entrega."""
        consulta = select(cls).where(
            cls.entrega_id == entrega_id
        )

        return db.session.scalars(consulta).all()

    @classmethod
    def existe_por_solicitud(cls, solicitud_detalle_id):
        """Indica si una solicitud ya fue entregada."""
        consulta = select(cls.id).where(
            cls.solicitud_detalle_id == solicitud_detalle_id
        )

        return db.session.scalar(consulta) is not None


class Entrega(BaseModel):
    """Representa a una entrega del sistema."""

    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    usuario_comedor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("usuarios.id"),
        nullable=False
    )

    usuario_comedor: Mapped["User"] = relationship(
        "User"
    )

    responsable_retiro: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    detalles: Mapped[list["EntregaDetalle"]] = relationship(
        back_populates="entrega",
        cascade="all, delete-orphan"
    )

    def guardar(self):
        """Guarda o actualiza una entrega."""
        db.session.add(self)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def obtener_entregas(cls):
        """Obtiene todas las entregas."""
        return db.session.scalars(
            select(cls).order_by(cls.fecha_hora.desc())
        ).all()

    @classmethod
    def obtener_por_id(cls, delivery_id):
        """Obtiene una entrega por su ID."""
        return db.session.get(cls, delivery_id)

    @classmethod
    def crear_con_detalles(
        cls,
        usuario_comedor_id,
        responsable_retiro,
        detalles
    ):
        """
        Crea una entrega y todos sus detalles
        dentro de una misma transacción.
        """

        entrega = cls(
            usuario_comedor_id=usuario_comedor_id,
            responsable_retiro=responsable_retiro
        )

        db.session.add(entrega)

        try:
            # Genera el ID de entrega sin hacer commit todavía
            db.session.flush()

            for item in detalles:
                detalle = EntregaDetalle(
                    entrega_id=entrega.id,
                    solicitud_detalle_id=item["solicitud_detalle_id"],
                    tipo_menu_entregado_id=item["tipo_menu_entregado_id"]
                )

                db.session.add(detalle)

            db.session.commit()

            return entrega

        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def buscar(
        cls,
        fecha=None,
        sector_id=None,
        tipo_comida=None
    ):
        """Busca entregas aplicando filtros y paginación."""
        consulta = select(cls)
        if sector_id is not None or tipo_comida is not None:
            consulta = (
                consulta
                .join(
                    EntregaDetalle,
                    EntregaDetalle.entrega_id == cls.id
                )
                .join(
                    SolicitudDetalle,
                    SolicitudDetalle.id == EntregaDetalle.solicitud_detalle_id
                )
                .join(
                    Pedido,
                    Pedido.id == SolicitudDetalle.pedido_id
                )
            )

        if fecha is not None:
            consulta = consulta.where(
                func.date(cls.fecha_hora) == fecha
            )

        if sector_id is not None:
            consulta = consulta.where(
                Pedido.sector_id == sector_id
            )

        if tipo_comida is not None:
            consulta = consulta.where(
                SolicitudDetalle.tipo_comida == tipo_comida
            )

        consulta = (
            consulta
            .distinct()
            .order_by(cls.fecha_hora.desc())
        )

        return paginate_query(consulta)

    @classmethod
    def usuario_tiene_entregas(cls, user_id):
        """Indica si un usuario registró alguna entrega."""

        consulta = select(cls.id).where(
            cls.usuario_comedor_id == user_id
        )

        return db.session.scalar(consulta) is not None

    @classmethod
    def obtener_resumen(
        cls,
        fecha=None,
        sector_id=None,
        tipo_comida=None
    ):
        """
        Obtiene totales de comidas autorizadas y entregadas
        agrupados por tipo de comida y tipo de menú.
        """

        # ==============================
        # AUTORIZADAS
        # ==============================

        consulta_autorizadas = (
            select(
                SolicitudDetalle.tipo_comida,
                TipoMenu.nombre,
                func.count(SolicitudDetalle.id)
            )
            .join(
                Pedido,
                Pedido.id == SolicitudDetalle.pedido_id
            )
            .join(
                TipoMenu,
                TipoMenu.id == SolicitudDetalle.tipo_menu_id
            )
            .where(
                SolicitudDetalle.estado_autorizacion == "autorizado"
            )
        )

        if fecha is not None:
            consulta_autorizadas = consulta_autorizadas.where(
                Pedido.fecha == fecha
            )

        if sector_id is not None:
            consulta_autorizadas = consulta_autorizadas.where(
                Pedido.sector_id == sector_id
            )

        if tipo_comida is not None:
            consulta_autorizadas = consulta_autorizadas.where(
                SolicitudDetalle.tipo_comida == tipo_comida
            )

        consulta_autorizadas = consulta_autorizadas.group_by(
            SolicitudDetalle.tipo_comida,
            TipoMenu.nombre
        )

        autorizadas = db.session.execute(
            consulta_autorizadas
        ).all()

        # ==============================
        # ENTREGADAS
        # ==============================

        consulta_entregadas = (
            select(
                SolicitudDetalle.tipo_comida,
                TipoMenu.nombre,
                func.count(EntregaDetalle.id)
            )
            .join(
                SolicitudDetalle,
                SolicitudDetalle.id
                == EntregaDetalle.solicitud_detalle_id
            )
            .join(
                Pedido,
                Pedido.id == SolicitudDetalle.pedido_id
            )
            .join(
                TipoMenu,
                TipoMenu.id
                == EntregaDetalle.tipo_menu_entregado_id
            )
        )

        if fecha is not None:
            consulta_entregadas = consulta_entregadas.where(
                Pedido.fecha == fecha
            )

        if sector_id is not None:
            consulta_entregadas = consulta_entregadas.where(
                Pedido.sector_id == sector_id
            )

        if tipo_comida is not None:
            consulta_entregadas = consulta_entregadas.where(
                SolicitudDetalle.tipo_comida == tipo_comida
            )

        consulta_entregadas = consulta_entregadas.group_by(
            SolicitudDetalle.tipo_comida,
            TipoMenu.nombre
        )

        entregadas = db.session.execute(
            consulta_entregadas
        ).all()

        # ==============================
        # ARMO LA RESPUESTA
        # ==============================

        resumen = {}

        for comida, nombre_menu, cantidad in autorizadas:
            clave = (
                comida,
                nombre_menu
            )

            resumen[clave] = {
                "tipo_comida": comida,
                "tipo_menu": nombre_menu,
                "autorizadas": cantidad,
                "entregadas": 0
            }

        for comida, nombre_menu, cantidad in entregadas:
            clave = (
                comida,
                nombre_menu
            )

            if clave not in resumen:
                resumen[clave] = {
                    "tipo_comida": comida,
                    "tipo_menu": nombre_menu,
                    "autorizadas": 0,
                    "entregadas": cantidad
                }
            else:
                resumen[clave]["entregadas"] = cantidad

        return list(
            resumen.values()
        )