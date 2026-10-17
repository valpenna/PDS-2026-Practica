from src.core.db import (
    db,
    BaseModel,
)  # importo la base de datos y la clase BaseModel para que los modelos hereden de ella
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    BigInteger,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    select,
    func,
    or_,
)
from datetime import datetime, timezone
from dataclasses import dataclass
from src.core.sectores import Sector
from src.core.tipos_menu import TipoMenu
from src.core.tipos_personal import TipoPersonal


@dataclass
class FiltrosPersonal:
    """Criterios de búsqueda, ordenamiento y paginación del listado de personal."""

    nombre: str | None = None
    apellido: str | None = None
    dni: str | None = None
    sector_id: int | None = None
    tipo_personal_id: int | None = None
    fecha: datetime | None = None
    activo: bool | None = None
    sector_jefe_id: int | None = None
    solo_residentes: bool = False
    pagina: int = 1
    por_pagina: int = 25
    ordenar_por: str = "nombre"
    direccion: str = "asc"


class Personal(BaseModel):
    """Modelo de Personal."""

    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    dni: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)

    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    apellido: Mapped[str] = mapped_column(String(50), nullable=False)

    tipo_personal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tipos_personal.id"), nullable=False
    )

    sector_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sectores.id"), nullable=True
    )  # Nulo para residentes

    menu_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tipos_menu.id"), nullable=False
    )

    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def listar_personal(cls):
        """Lista todo el personal activo desde la base de datos."""
        stmt = select(cls).where(cls.activo == True)
        return db.session.scalars(stmt).all()

    @classmethod
    def buscar(cls, filtros: FiltrosPersonal):
        """Busca y pagina personal aplicando los filtros del listado."""
        por_pagina = min(max(int(filtros.por_pagina or 25), 1), 25)
        consulta = (
            select(cls, TipoPersonal.nombre, Sector.nombre, TipoMenu.nombre)
            .join(TipoPersonal, cls.tipo_personal_id == TipoPersonal.id)
            .outerjoin(Sector, cls.sector_id == Sector.id)
            .join(TipoMenu, cls.menu_id == TipoMenu.id)
        )

        if filtros.nombre:
            consulta = consulta.where(cls.nombre.ilike(f"%{filtros.nombre}%"))

        if filtros.apellido:
            consulta = consulta.where(cls.apellido.ilike(f"%{filtros.apellido}%"))

        if filtros.dni:
            consulta = consulta.where(cls.dni.ilike(f"%{filtros.dni}%"))

        if filtros.sector_id is not None:
            consulta = consulta.where(cls.sector_id == filtros.sector_id)

        if filtros.activo is not None:
            consulta = consulta.where(cls.activo == filtros.activo)

        if filtros.tipo_personal_id is not None:
            consulta = consulta.where(cls.tipo_personal_id == filtros.tipo_personal_id)

        # if filtros.fecha is not None:
        #     consulta = consulta.where(
        #         cls.fecha == filtros.fecha
        #     )

        if filtros.solo_residentes:
            consulta = consulta.where(TipoPersonal.nombre == "Residente")
        elif filtros.sector_jefe_id is not None:
            consulta = consulta.where(
                or_(
                    cls.sector_id == filtros.sector_jefe_id,
                    TipoPersonal.nombre == "Residente",
                )
            )

        total = db.session.scalar(
            select(func.count())
            .select_from(consulta.with_only_columns(cls.id).order_by(None).subquery())
        ) or 0

        if filtros.ordenar_por == "fecha":
            columnas_orden = [cls.fecha_creacion]
        elif filtros.ordenar_por == "dni":
            columnas_orden = [cls.dni, cls.apellido, cls.nombre]
        else:
            columnas_orden = [cls.apellido, cls.nombre]

        if filtros.direccion == "desc":
            consulta = consulta.order_by(
                *(columna.desc() for columna in columnas_orden)
            )
        else:
            consulta = consulta.order_by(*(columna.asc() for columna in columnas_orden))

        offset = (filtros.pagina - 1) * por_pagina
        consulta = consulta.offset(offset).limit(por_pagina)
        return db.session.execute(consulta).all(), total

    @classmethod
    def obtener_personal_por_id(cls, personal_id):
        """
        Obtiene el personal con el id especificado.
        """
        return db.session.get(cls, personal_id)

    @classmethod
    def obtener_por_dni(cls, dni):
        """Obtiene un registro de personal por su DNI."""
        stmt = select(cls).where(cls.dni == dni)
        return db.session.scalar(stmt)

    @classmethod
    def obtener_por_sector(cls, sector_id):
        """Lista todo el personal con sector desde la base de datos."""
        stmt = select(cls).where(cls.sector_id == sector_id)
        return db.session.scalar(stmt)

    @classmethod
    def obtener_todos(cls):
        """Lista todo el personal desde la base de datos."""
        stmt = select(cls)
        return db.session.scalars(stmt).all()

    @classmethod
    def crear_personal(cls, datos_personal):
        """
        Crea un nuevo personal con los datos proporcionados.
        """
        nuevo_personal = cls(**datos_personal)
        db.session.add(nuevo_personal)
        db.session.commit()
        return nuevo_personal

    @classmethod
    def actualizar_personal(cls, personal_id, datos_actualizados):
        """
        Actualiza los datos del personal con el id especificado.
        """
        personal = db.session.get(cls, personal_id)
        if personal:
            for key, value in datos_actualizados.items():
                setattr(personal, key, value)
            db.session.commit()
            return personal
        return "No se encontro el personal con el id especificado"

    @classmethod
    def tiene_historial(cls, personal_id: int) -> bool:
        """Indica si la persona aparece en detalles de pedidos."""
        from src.core.solicitudes_detalle import SolicitudDetalle

        return SolicitudDetalle.existe_por_persona(personal_id)

    @classmethod
    def eliminar_personal(cls, personal_id):
        """
        Elimina el personal con el id especificado.
        """
        personal = db.session.get(cls, personal_id)
        if personal:
            db.session.delete(personal)
            db.session.commit()
            return f"Personal con id {personal_id} eliminado."
        return "No se encontro el personal con el id especificado"

    @classmethod
    def marcar_como_inactivo(cls, personal_id):
        """
        Marca el personal con el id especificado como inactivo.
        """
        personal = db.session.get(cls, personal_id)
        if personal:
            personal.activo = False
            db.session.commit()
            return f"Personal con id {personal_id} marcado como inactivo."
        return "No se encontro el personal con el id especificado"
