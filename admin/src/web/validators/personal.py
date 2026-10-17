from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
)
from src.core.personal import Personal
from src.core.sectores import Sector
from src.core.tipos_personal import TipoPersonal
from src.core.tipos_menu import TipoMenu
from src.web.helpers.text import normalizar_texto


class PersonalBaseValidator(BaseModel):
    """Validaciones comunes para creación y edición de personal."""

    dni: str
    nombre: str
    apellido: str
    tipo_personal_id: int
    sector_id: int | None = None
    menu_id: int
    activo: bool

    @field_validator("dni")
    @classmethod
    def validar_dni(cls, valor):
        """Valida el formato y longitud del DNI."""
        if not valor or len(valor) < 7:
            raise ValueError(
                "El DNI debe tener al menos 7 caracteres."
            )

        if len(valor) > 12:
            raise ValueError(
                "El DNI no puede tener más de 12 caracteres."
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
        if not valor or len(valor) < 2:
            raise ValueError(
                "El nombre o apellido debe tener al menos 2 caracteres."
            )

        if len(valor) > 50:
            raise ValueError(
                "El nombre o apellido no puede tener más de 50 caracteres."
            )

        if not valor.replace(" ", "").isalpha():
            raise ValueError(
                "El nombre o apellido debe contener solo letras y espacios."
            )

        return valor

    @field_validator("tipo_personal_id", mode="before")
    @classmethod
    def validar_tipo_personal_id(cls, valor):
        """Convierte un valor numérico a entero y rechaza valores inválidos."""
        if valor is None or valor == "":
            raise ValueError(
                "Debe seleccionar un tipo de personal."
            )

        if not str(valor).isdigit():
            raise ValueError(
                "El tipo de personal seleccionado no es válido."
            )

        valor = int(valor)
        if valor <= 0:
            raise ValueError(
                "El tipo de personal seleccionado no es válido."
            )

        return valor

    @field_validator("sector_id", mode="before")
    @classmethod
    def validar_sector_id(cls, valor):
        """Convierte valores numéricos a entero y los vacíos a None."""
        if valor == "" or valor is None:
            return None

        if not str(valor).isdigit():
            raise ValueError(
                "El sector seleccionado no es válido."
            )

        valor = int(valor)
        if valor <= 0:
            raise ValueError(
                "El sector seleccionado no es válido."
            )

        return valor

    @field_validator("menu_id", mode="before")
    @classmethod
    def validar_menu_id(cls, valor):
        """Convierte un valor numérico a entero y rechaza valores inválidos."""
        if valor is None or valor == "":
            raise ValueError(
                "Debe seleccionar un menú."
            )

        if not str(valor).isdigit():
            raise ValueError(
                "El menú seleccionado no es válido."
            )

        valor = int(valor)
        if valor <= 0:
            raise ValueError(
                "El menú seleccionado no es válido."
            )

        return valor


class PersonalCrearValidator(PersonalBaseValidator):
    """Validaciones específicas para crear personal."""


class PersonalEditarValidator(PersonalBaseValidator):
    """Validaciones específicas para editar personal."""


def validar_personal_creacion(data):
    """Valida los datos de creación y comprueba que el DNI no esté registrado."""
    try:
        datos = PersonalCrearValidator.model_validate(data)
    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_tipo_personal(datos)
    errores.update(validar_sector(datos))
    errores.update(validar_menu(datos))
    if Personal.obtener_por_dni(datos.dni):
        errores["dni"] = "Ya existe un personal con ese DNI."

    return datos, errores


def validar_personal_edicion(data, personal):
    """Valida la edición y rechaza un DNI usado por otro registro."""
    try:
        datos = PersonalEditarValidator.model_validate(data)
    except ValidationError as error:
        return None, formatear_errores(error)

    errores = validar_tipo_personal(datos)
    errores.update(validar_sector(datos))
    errores.update(validar_menu(datos))
    personal_con_mismo_dni = Personal.obtener_por_dni(datos.dni)
    if personal_con_mismo_dni and personal_con_mismo_dni.id != personal.id:
        errores["dni"] = "Ya existe otro personal con ese DNI."

    return datos, errores


def validar_tipo_personal(datos):
    """Comprueba que el tipo exista y aplica la obligatoriedad de sector para Personal Fijo."""
    errores = {}
    tipo_personal = TipoPersonal.obtener_por_id(datos.tipo_personal_id)

    if tipo_personal is None:
        errores["tipo_personal_id"] = "El tipo de personal seleccionado no existe."
    elif tipo_personal.nombre == "Personal Fijo" and datos.sector_id is None:
        errores["sector_id"] = (
            "El personal fijo debe tener un sector asignado obligatoriamente."
        )

    return errores


def validar_sector(datos):
    """Comprueba que el sector exista y esté activo."""
    errores = {}

    if datos.sector_id is None:
        return errores

    sector = Sector.obtener_por_id(datos.sector_id)
    if sector is None:
        errores["sector_id"] = "El sector seleccionado no existe."
    elif not sector.activo:
        errores["sector_id"] = "No se puede asignar un sector inactivo."

    return errores


def validar_menu(datos):
    """Comprueba que el ID de menú exista."""
    if TipoMenu.obtener_por_id(datos.menu_id) is None:
        return {"menu_id": "El menú seleccionado no existe."}

    return {}


def buscar_tipo_personal(nombre: str):
    """Busca un tipo de personal por nombre, ignorando mayúsculas y tildes.

    Devuelve el tipo encontrado o None si no existe.
    """
    nombre_norm = normalizar_texto(nombre)
    for tipo in TipoPersonal.obtener_todos():
        if normalizar_texto(tipo.nombre) == nombre_norm:
            return tipo
    return None


def buscar_sector(nombre: str):
    """Busca un sector por nombre, ignorando mayúsculas y tildes.

    Devuelve el sector encontrado o None si no existe.
    """
    nombre_norm = normalizar_texto(nombre)
    for sector in Sector.obtener_todos():
        if normalizar_texto(sector.nombre) == nombre_norm:
            return sector
    return None


def buscar_menu(nombre: str):
    """Busca un tipo de menú por nombre, ignorando mayúsculas y tildes.

    Devuelve el menú encontrado o None si no existe.
    """
    nombre_norm = normalizar_texto(nombre)
    for menu in TipoMenu.obtener_todos():
        if normalizar_texto(menu.nombre) == nombre_norm:
            return menu
    return None


def validar_fila_csv(fila, dnis_en_csv):
    """Valida una fila de CSV para importar personal traduciendo nombres a IDs."""
    errores = {}

    dni = (fila.get("dni") or "").strip()
    nombre = (fila.get("nombre") or "").strip()
    apellido = (fila.get("apellido") or "").strip()
    nombre_tipo = (fila.get("tipo_personal") or "").strip()
    nombre_sector = (fila.get("sector") or "").strip()
    nombre_menu = (fila.get("menu") or "").strip()

    # 1. Chequear duplicado dentro del mismo archivo CSV
    if dni and dni in dnis_en_csv:
        errores["dni"] = "Está duplicado dentro del archivo CSV."
    elif dni:
        dnis_en_csv.add(dni)

    # 2. Traducir Tipo de Personal a ID (tolerante a mayúsculas/tildes)
    tipo_personal = buscar_tipo_personal(nombre_tipo) if nombre_tipo else None
    if not tipo_personal:
        errores["tipo_personal"] = f"El tipo de personal '{nombre_tipo}' no es válido."
    tipo_personal_id = tipo_personal.id if tipo_personal else None

    # 3. Traducir Sector a ID (si vino texto)
    sector_id = None
    if nombre_sector:
        sector = buscar_sector(nombre_sector)
        if not sector:
            errores["sector"] = f"El sector '{nombre_sector}' no existe."
        elif not sector.activo:
            errores["sector"] = f"El sector '{nombre_sector}' está inactivo."
        else:
            sector_id = sector.id

    # 4. Traducir Menú a ID (tolerante a mayúsculas/tildes)
    menu = buscar_menu(nombre_menu) if nombre_menu else None
    if not menu:
        errores["menu"] = f"El menú '{nombre_menu}' no es válido."
    menu_id = menu.id if menu else None

    # Si hubo error en los catálogos o DNI duplicado en CSV, frenamos acá
    if errores:
        return None, errores

    # 5. Pasamos por validar_personal_creacion para reutilizar todas las reglas
    # (valida formato de DNI, nombre, apellido, unicidad de DNI en BD,
    # y exige sector para Personal Fijo pero NO para Residente)
    datos, errores_validacion = validar_personal_creacion({
        "dni": dni,
        "nombre": nombre,
        "apellido": apellido,
        "tipo_personal_id": tipo_personal_id,
        "sector_id": sector_id,
        "menu_id": menu_id,
        "activo": True,
    })

    if errores_validacion:
        errores.update(errores_validacion)
        return None, errores

    return datos, errores

def formatear_errores(error):
    """Convierte los errores de Pydantic en un diccionario por campo."""
    errores = {}

    for detalle in error.errors():
        ubicacion = detalle["loc"]
        campo = ubicacion[0] if ubicacion else "general"
        errores[campo] = detalle["msg"].replace("Value error, ", "")

    return errores
