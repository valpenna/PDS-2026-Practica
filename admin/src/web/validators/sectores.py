from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from src.core.sectores import Sector
from src.core.usuarios import User


class SectoresBaseValidator(BaseModel):
    """Validaciones comunes para creación y edición de sectores."""

    nombre: str
    descripcion: str
    activo: bool
    jefes_servicio: list

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor):
        """Valida el formato y longitud del nombre."""
        if not valor:
            raise ValueError("El campo está vacío.")
        if len(valor) < 2:
            raise ValueError("Debe tener al menos 2 caracteres.")

        if len(valor) > 100:
            raise ValueError("No puede superar los 100 caracteres.")

        return valor

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor):
        """Valida el formato y longitud del descripcion"""

        if len(valor) > 150:
            raise ValueError("No puede superar los 150 caracteres.")

        return valor


class SectorCrearValidator(SectoresBaseValidator):
    """Validaciones específicas para crear un sector."""

    @field_validator("nombre")
    @classmethod
    def validar_nombre_unico(cls, valor):
        """Valida que no exista otro sector con el mismo nombre."""
        if Sector.obtener_por_nombre(valor):
            raise ValueError("Ya existe un sector con ese nombre.")
        return valor


class SectorEdicionValidator(SectoresBaseValidator):
    """Validaciones específicas para editar un sector."""

    @field_validator("nombre")
    @classmethod
    def validar_nombre_unico(cls, valor):
        """Valida que no exista otro sector con el mismo nombre."""

        if Sector.obtener_por_nombre(valor):
            raise ValueError("Ya existe un sector con ese nombre.")
        return valor


def validar_sector_edicion(data, sector_id):
    """Valida los datos necesarios para editar un sector."""
    try:
        sector = Sector.obtener_por_nombre(data.get("nombre"))
        if sector and sector.id != sector_id:
            datos = SectorEdicionValidator.model_validate(data)
        else:
            datos = SectoresBaseValidator.model_validate(data)
    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_jefes_sector(datos, sector_id)

    return datos, errores


def validar_sector_creacion(data):
    """Valida los datos necesarios para crear un sector."""
    try:
        datos = SectorCrearValidator.model_validate(data)
    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_jefes_sector(datos)

    return datos, errores


def validar_jefes_sector(datos, sector_id=None):
    """Valida que los usuarios seleccionados existan y"""
    errores = {}

    jefes_servicio = datos.jefes_servicio
    if jefes_servicio:
        for jefe in jefes_servicio:
            try:
                user = User.obtener_por_id(int(jefe))
            except (TypeError, ValueError):
                user = None
            if not user:
                errores["jefe_servicio"] = "El usuario no existe"
            elif user.rol_id != 2:
                errores["jefe_servicio"] = (
                    f"El usuario {user.nombre} seleccionado no es un Jefe de servicio"
                )
            elif not user.activo and (sector_id is None or user.sector_id != sector_id):
                errores["jefe_servicio"] = f"El usuario {user.nombre} está inactivo"
            elif (
                user.sector_id is not None
                and user.sector_id != ""
                and user.sector_id != sector_id
            ):
                errores["jefe_servicio"] = (
                    f"El usuario {user.nombre} ya tiene un sector asignado"
                )
    return errores


def formatear_errores(error):
    """Convierte los errores de Pydantic al formato del formulario."""

    errores = {}

    for detalle in error.errors():
        ubicacion = detalle["loc"]

        if ubicacion:
            campo = ubicacion[0]
        else:
            campo = "general"

        mensaje = detalle["msg"].replace(
            "Value error, ",
            "",
        )

        errores[campo] = mensaje

    return errores
