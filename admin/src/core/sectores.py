from datetime import datetime, timezone
from src.web.helpers.paginator import paginate_query
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship
from dataclasses import dataclass
from src.core.db import db, BaseModel


@dataclass
class FiltrosSector:
    nombre: str | None = None
    activo: bool | None = None
    ordenar_por: str = "nombre"
    direccion: str = "asc"
    con_jefes: bool = False


class Sector(BaseModel):
    """Representa a un sector del sistema."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los sectores."""
        consulta = select(cls).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_todos_con_jefes(cls):
        """Obtiene todos los sectores con sus respectivos jefes."""
        from src.core.usuarios import User

        consulta = select(cls).order_by(cls.id)
        sectores = db.session.scalars(consulta).all()
        for sector in sectores:
            sector.jefes_servicio = User.obtener_por_sector(sector.id)
        return sectores

    @classmethod
    def obtener_todos_activos(cls):
        """Obtiene todos los sectores activos."""
        consulta = select(cls).where(cls.activo == True).order_by(cls.id)
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_por_id(cls, sector_id):
        """Obtiene un sector por su ID."""
        return db.session.get(cls, sector_id)

    @classmethod
    def obtener_por_nombre(cls, nombre):
        """Obtiene un sector por su nombre."""
        consulta = select(cls).where(cls.nombre == nombre)
        return db.session.scalar(consulta)

    @classmethod
    def eliminar_sector(cls, sector_id):
        """Elimina un sector por su ID."""
        sector = cls.obtener_por_id(sector_id)
        if sector:
            db.session.delete(sector)
            db.session.commit()
            return True

    @classmethod
    def buscar(cls, filtros: FiltrosSector):
        """Obtiene los sectores a partir de lo que se filtre."""
        from src.core.usuarios import User

        consulta = select(cls)
        consulta = cls._aplicar_filtros(consulta, filtros)
        consulta = cls._aplicar_ordenamiento(consulta, filtros)
        paginados = paginate_query(consulta)
        for paginado in paginados.items:
            paginado.jefes_servicio = User.obtener_por_sector(paginado.id)
        return paginados

    @classmethod
    def _aplicar_filtros(cls, consulta, filtros):
        """Aplica los filtros a la consulta."""
        if filtros.nombre:
            consulta = consulta.where(cls.nombre.ilike(f"%{filtros.nombre}%"))

        if filtros.activo is not None:
            consulta = consulta.where(cls.activo == filtros.activo)

        if filtros.con_jefes is not None:
            from src.core.usuarios import User

            subconsulta = select(User.sector_id).where(User.rol_id == 2).distinct()
            if filtros.con_jefes is True:
                consulta = consulta.where(cls.id.in_(subconsulta))
            elif filtros.con_jefes is False:
                consulta = consulta.where(cls.id.not_in(subconsulta))

        return consulta

    @classmethod
    def _aplicar_ordenamiento(cls, consulta, filtros):
        """Aplica el ordenamiento a la consulta."""

        if filtros.ordenar_por == "fecha":
            if filtros.direccion == "desc":
                consulta = consulta.order_by(cls.fecha_creacion.desc())
            else:
                consulta = consulta.order_by(cls.fecha_creacion.asc())

        elif filtros.ordenar_por == "nombre":
            if filtros.direccion == "desc":
                consulta = consulta.order_by(cls.nombre.desc())
            else:
                consulta = consulta.order_by(cls.nombre.asc())

        else:
            if filtros.direccion == "desc":
                consulta = consulta.order_by(cls.id.desc())
            else:
                consulta = consulta.order_by(cls.id.asc())
        return consulta

    def guardar(self):
        """Guarda el usuario actual en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
