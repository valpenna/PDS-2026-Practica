from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    model_validator,
    ConfigDict
)
from src.core.usuarios import User
from src.core.personal import Personal
from src.core.roles import Role,NombreRol

class UsuarioBaseValidator(BaseModel):
    """Validaciones comunes para creación y edición de usuarios."""
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    nombre: str
    apellido: str
    dni: str
    activo: bool
    rol_id: int = Field(gt=0)
   
    @field_validator("dni")
    @classmethod
    def validar_dni(cls, valor):
        """Valida el formato y longitud del DNI."""
        if  not valor:
             raise ValueError(
                "El DNI esta vacío."
            )

        if len(valor) < 7:
            raise ValueError(
                "El DNI debe tener al menos 7 caracteres."
            )

        if len(valor) > 20:
            raise ValueError(
                "El DNI no puede superar los 20 caracteres."
            )

        if not valor.isdigit():
            raise ValueError(
                "El DNI debe contener solo números."
            )

        return valor

    @field_validator("nombre", "apellido")
    @classmethod
    def validar_nombre_apellido(cls, valor):
        """Valida el formato y longitud del nombre y apellido."""
        if  not valor:
            raise ValueError(
                "El campo está vacío."
            )
        if len(valor) < 2:
            raise ValueError(
                "Debe tener al menos 2 caracteres."
            )

        if len(valor) > 100:
            raise ValueError(
                "No puede superar los 100 caracteres."
            )

        if not valor.replace(" ", "").isalpha():
            raise ValueError(
                "Solo se permiten letras."
            )

        return valor

    @field_validator("rol_id", mode="before")
    @classmethod
    def validar_rol_id_numero(cls, valor):
        """Valida que el rol sea numérico."""

        if valor is None or valor == "":
            raise ValueError(
                "Debe seleccionar un rol."
            )

        if not str(valor).isdigit():
            raise ValueError(
                "El rol seleccionado no es válido."
            )

        return valor


class UsuarioCrearValidator(UsuarioBaseValidator):
    """Validaciones específicas para crear un usuario."""

    password: str
    password_confirmacion: str

    @field_validator("password")
    @classmethod
    def validar_password_obligatoria(cls, valor):
        """Valida que la contraseña sea obligatoria."""

        if not valor:
            raise ValueError(
                "La contraseña es obligatoria."
            )
        if len(valor) < 8:
            raise ValueError(
                "La contraseña debe tener al menos 8 caracteres."
            )

        return valor

    @field_validator("password_confirmacion")
    @classmethod
    def validar_confirmacion_obligatoria(cls, valor):
        """Valida que se confirme la contraseña."""

        if not valor:
            raise ValueError(
                "Debe confirmar la contraseña."
            )
        
        if len(valor) < 8:
            raise ValueError(
                "La contraseña debe tener al menos 8 caracteres."
            )

        return valor

    @model_validator(mode="after")
    def validar_passwords_coinciden(self):
        """Valida que ambas contraseñas coincidan."""

        if self.password != self.password_confirmacion:
            raise ValueError(
                "Las contraseñas no coinciden."
            )

        return self


class UsuarioEditarValidator(UsuarioBaseValidator):
    """Validaciones específicas para editar un usuario."""

    password: str | None = None
    password_confirmacion: str | None = None

    @field_validator(
        "password",
        "password_confirmacion",
        mode="before",
    )
    @classmethod
    def password_vacia_a_none(cls, valor):
        """Convierte una contraseña vacía en None."""

        if valor == "":
            return None

        return valor
    
    @field_validator("password", "password_confirmacion")
    @classmethod
    def validar_longitud_password(cls, valor):
        """Valida la longitud de la nueva contraseña."""

        if valor is not None and len(valor) < 8:
            raise ValueError(
                "La contraseña debe tener al menos 8 caracteres."
            )

        return valor
    
    @model_validator(mode="after")
    def validar_passwords_coinciden(self):
        """Valida las contraseñas solamente si se desea cambiarlas."""

        if self.password or self.password_confirmacion:
            if self.password != self.password_confirmacion:
                raise ValueError(
                    "Las contraseñas no coinciden."
                )

        return self


def validar_usuario_creacion(data):
    """Valida los datos necesarios para crear un usuario."""

    try:
        datos = UsuarioCrearValidator.model_validate(data)

    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_rol_sector(datos)

    if User.obtener_por_email(datos.email):
        errores["email"] = (
            "Ya existe un usuario con ese correo electrónico."
        )

    if User.obtener_por_dni(datos.dni):
        errores["dni"] = (
            "Ya existe un usuario con ese DNI."
        )

    return datos, errores


def validar_usuario_edicion(data,usuario):
    """Valida los datos necesarios para editar un usuario."""

    try:
        datos = UsuarioEditarValidator.model_validate(data)

    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_rol_sector(datos)
    usuario_email = User.obtener_por_email(datos.email)

    if usuario_email and usuario_email.id != usuario.id:
        errores["email"] = (
            "Ya existe otro usuario con ese correo electrónico."
        )

    usuario_dni = User.obtener_por_dni(datos.dni)

    if usuario_dni and usuario_dni.id != usuario.id:
        errores["dni"] = (
            "Ya existe otro usuario con ese DNI."
        )

    return datos, errores


def validar_rol_sector(datos):
    errores = {}

    rol = Role.obtener_por_id(datos.rol_id)

    if rol is None:
        errores["rol_id"] = "El rol seleccionado no existe."
        return errores
    
    if rol.nombre == NombreRol.ADMINISTRADOR.value and not datos.activo:
        errores["activo"] = (
            "Un usuario Administrador no puede estar inactivo."
        )
        
    if rol.nombre == NombreRol.JEFE_SERVICIO.value:
        personal = Personal.obtener_por_dni(datos.dni)

        if personal is None:
            errores["personal"] = (
                "El Jefe de Servicio debe estar cargado previamente como Personal."
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
        if campo == "email":
            mensaje = "Ingrese un correo electrónico válido."
        errores[campo] = mensaje

    return errores