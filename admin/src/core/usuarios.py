from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, select,func
from sqlalchemy.orm import Mapped, mapped_column,relationship
from dataclasses import dataclass
from src.core.db import db, BaseModel
from src.core.roles import Role,NombreRol
from src.core.sectores import Sector
from  src.web.helpers.paginator import paginate_query
from src.core.pedidos import Pedido
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.entregas import Entrega

@dataclass
class FiltrosUsuario:
    email: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    dni: str | None = None
    activo: bool | None = None
    rol_id: int | None = None
    sector_id: int | None = None
    ordenar_por: str = "apellidoYnombre"
    direccion: str = "asc"
class User(BaseModel):
    """Representa a un usuario del sistema."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    apellido: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    dni: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    rol_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id"),
        nullable=False
    )

    rol: Mapped[Role] = relationship()

    sector_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sectores.id"),
        nullable=True
    )
    sector: Mapped[Sector | None] = relationship()
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now
    )

    fecha_modificacion: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now
    )

    @classmethod
    def obtener_todos(cls):
        """Obtiene todos los usuarios ordenados por apellido y nombre."""
        consulta = select(cls).order_by(cls.apellido, cls.nombre)
        return db.session.scalars(consulta).all()

    @classmethod
    def obtener_todos_activos(cls):
        """Obtiene los usuarios ordenados por apellido y nombre que esten activos."""
        consulta = select(cls).where(cls.activo).order_by(cls.apellido, cls.nombre)
        return db.session.scalars(consulta).all()
    
    @classmethod
    def obtener_por_id(cls, user_id):
        """Obtiene un usuario por su identificador."""
        return db.session.get(cls, user_id)


    @classmethod
    def obtener_por_email(cls, email):
        """Obtiene un usuario por su correo electrónico."""
        consulta = select(cls).where(cls.email == email)
        return db.session.scalar(consulta)


    @classmethod
    def obtener_por_dni(cls, dni):
        """Obtiene un usuario por su DNI."""
        consulta = select(cls).where(cls.dni == dni)
        return db.session.scalar(consulta)
    
    @classmethod
    def obtener_permisos(cls, user_id):
        """Obtiene todos los permisos de un usuario."""
        usuario = cls.obtener_por_id(user_id)
    
        if usuario is None or not usuario.activo or usuario.rol is None:
            return []
        
        permisos = []

        for rol_permiso in usuario.rol.roles_permisos:
            permisos.append(rol_permiso.permiso)

        return permisos
    
    @classmethod
    def tiene_permiso(cls, user_id, nombre_permiso):
        """Indica si un usuario tiene un permiso."""
        permisos = cls.obtener_permisos(user_id)

        for permiso in permisos:
            if permiso.nombre == nombre_permiso:
                return True

        return False
    
    @classmethod
    def obtener_rol_usuario(cls, user_id):
        """Obtiene el rol del usuario."""
        usuario = cls.obtener_por_id(user_id)
        
        if usuario is None or usuario.rol is None:
            return None
        
        return usuario.rol

    @classmethod
    def tiene_rol(cls, user_id, nombre_rol):
        """Indica si el usuario tiene un rol determinado."""
        rol = cls.obtener_rol_usuario(user_id)

        if rol is None:
            return False

        return rol.nombre == nombre_rol

    @classmethod
    def obtener_por_sector(cls,id_sector):
        """Devuelve todos los usuarios pertenecientes al sector que recibe como parametro."""
        consulta = select(cls).where(cls.sector_id ==id_sector)
        return db.session.scalars(consulta).all()
    
    @classmethod
    def obtener_jefes_de_servicio(cls):
        """Devuelve todos los usuarios jefes de servicio."""
        consulta = (select(cls).join(cls.rol).where(Role.nombre == NombreRol.JEFE_SERVICIO.value).order_by(cls.apellido, cls.nombre))
        return db.session.scalars(consulta).all()
    
    @classmethod
    def buscar(cls, filtros: FiltrosUsuario):
        """Obtiene los usuarios a partir de los filtros."""

        consulta = select(cls)

        consulta = cls._aplicar_filtros(
            consulta,
            filtros
        )

        consulta = cls._aplicar_ordenamiento(
            consulta,
            filtros
        )

        return paginate_query(consulta)


    @classmethod
    def _aplicar_filtros(cls, consulta, filtros):
        """Aplica los filtros a la consulta."""

        if filtros.email:
            consulta = consulta.where(
                cls.email == filtros.email
            )

        if filtros.nombre:
            consulta = consulta.where(
                cls.nombre.ilike(f"%{filtros.nombre}%")
            )

        if filtros.apellido:
            consulta = consulta.where(
                cls.apellido.ilike(f"%{filtros.apellido}%")
            )

        if filtros.dni:
            consulta = consulta.where(
                cls.dni.ilike(f"%{filtros.dni}%")
            )

        if filtros.activo is not None:
            consulta = consulta.where(
                cls.activo == filtros.activo
            )

        if filtros.rol_id:
            consulta = consulta.where(
                cls.rol_id == filtros.rol_id
            )

        if filtros.sector_id:
            consulta = consulta.where(
                cls.sector_id == filtros.sector_id
            )

        return consulta

    @classmethod
    def _aplicar_ordenamiento(cls, consulta, filtros):
        """Aplica el ordenamiento a la consulta."""

        if filtros.ordenar_por == "fecha":
            if filtros.direccion == "desc":
                consulta = consulta.order_by(
                    cls.fecha_creacion.desc()
                )
            else:
                consulta = consulta.order_by(
                    cls.fecha_creacion.asc()
                )

        elif filtros.ordenar_por == "email":
            if filtros.direccion == "desc":
                consulta = consulta.order_by(
                    cls.email.desc()
                )
            else:
                consulta = consulta.order_by(
                    cls.email.asc()
                )

        else:
            if filtros.direccion == "desc":
                consulta = consulta.order_by(
                    cls.apellido.desc(),
                    cls.nombre.desc()
                )
            else:
                consulta = consulta.order_by(
                    cls.apellido.asc(),
                    cls.nombre.asc()
                )

        return consulta

    def guardar(self):
        """Guarda el usuario actual en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


    def eliminar(self):
        """Elimina el usuario actual de la base de datos."""
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        
    def desactivar(self):
        """Desactiva el usuario sin eliminarlo de la base de datos."""

        if self.rol.nombre == NombreRol.ADMINISTRADOR.value:
            raise ValueError("Los usuarios administradores no pueden ser desactivados.")

        self.activo = False

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def tiene_operaciones_asociadas(self):
        """Chequea si el usuario tiene pedidos, entregas o validaciones asociadas."""
        tiene_pedidos = len(Pedido.obtener_por_creador(self.id)) > 0
        tiene_entregas = Entrega.usuario_tiene_entregas(self.id)
        tiene_validaciones=SolicitudDetalle.participo_en_validaciones(self.id)
        return tiene_pedidos or tiene_entregas or tiene_validaciones
    
    @classmethod
    def cantidad_administradores(cls):
        """Chequea la cantidad de user admins que hay."""
        consulta = (
            select(func.count(cls.id))
            .join(Role, Role.id == cls.rol_id)
            .where(
                Role.nombre == NombreRol.ADMINISTRADOR,
                cls.activo == True,
            )
        )

        return db.session.scalar(consulta) or 0