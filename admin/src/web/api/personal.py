from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest, Conflict, Forbidden, HTTPException, NotFound
from src.web.schemas.personal import (
    personal_entrada_schema,
    personal_filtrar_schema,
    personal_sector_query_schema,
    personal_salida_schema,
    personal_actualizacion_schema,
)
from src.core.personal import FiltrosPersonal, Personal
from src.core.roles import NombreRol
from src.core.sectores import Sector
from src.core.tipos_menu import TipoMenu
from src.core.tipos_personal import TipoPersonal
from src.web.api.helpers import api_role_required, token_required

personal_api_bp = Blueprint(
    "api_personal", __name__, url_prefix="/api/personnel"
)
personal_sector_api_bp = Blueprint(
    "api_personal_sector", __name__, url_prefix="/api/sectors"
)


@personal_api_bp.errorhandler(ValidationError)
@personal_sector_api_bp.errorhandler(ValidationError)
def datos_invalidos(error):
    """Devuelve los errores de validación de entrada con estado HTTP 400."""
    return (
        jsonify(
            error={
                "code": "validation_error",
                "fields": error.messages,
            }
        ),
        400,
    )


@personal_api_bp.errorhandler(HTTPException)
@personal_sector_api_bp.errorhandler(HTTPException)
def error_http(error):
    """Serializa una excepción HTTP conservando su código de estado."""
    mensaje = (
        "Los datos ingresados son inválidos."
        if isinstance(error, BadRequest)
        else error.description
    )
    return (
        jsonify(
            error={
                "code": f"http_{error.code}",
                "message": mensaje,
            }
        ),
        error.code,
    )


@personal_api_bp.get("")  # buscar y listar personal
@token_required
@api_role_required(
    NombreRol.JEFE_SERVICIO,
    NombreRol.ALIMENTACION,
    NombreRol.COMEDOR,
)
def listar():
    """
    Proposito: Busca y lista personal aplicando filtros y paginacion.
    Entrada: Filtros opcionales por query: DNI, nombre, apellido, sector,
    tipo de personal, estado, pagina y cantidad por pagina.
    Salida: JSON con el listado de personal y los datos de paginacion.
    """
    # request.args trae los parametros de la url, con el schema, los paso a formato json
    usuario = g.current_user
    parametros = personal_filtrar_schema.load(request.args)
    # si los filtros no son validos, el schema lanza excepcion

    sector_jefe_id = None
    solo_residentes = False
    if (
        usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value
    ):  # si quien llama es jefe de servicio, pasa el if
        sector_jefe_id = usuario.sector_id  # se ontiene el sector
        solo_residentes = sector_jefe_id is None  # verificar regla de negocio
        parametros["sector_id"] = None

    filtros = FiltrosPersonal(
        **parametros,
        sector_jefe_id=sector_jefe_id,
        solo_residentes=solo_residentes,
    )
    resultados, total = Personal.buscar(filtros)

    personal_listado = []
    for personal, tipo_personal_nombre, sector_nombre, tipo_menu_nombre in resultados:
        personal_listado.append(
            personal_salida_schema.dump(
                {
                    "id": personal.id,
                    "dni": personal.dni,
                    "nombre": personal.nombre,
                    "apellido": personal.apellido,
                    "tipo_personal": {
                        "id": personal.tipo_personal_id,
                        "nombre": tipo_personal_nombre,
                    },
                    "sector": (
                        {"id": personal.sector_id, "nombre": sector_nombre}
                        if personal.sector_id is not None
                        else None
                    ),
                    "tipo_menu": {
                        "id": personal.menu_id,
                        "nombre": tipo_menu_nombre,
                    },
                    "activo": personal.activo,
                }
            )
        )

    return (
        jsonify(
            {
                "data": personal_listado,
                "total": total,
                "page": filtros.pagina,
                "per_page": filtros.por_pagina,
            }
        ),
        200,
    )


@personal_api_bp.get("/<int:personal_id>")
@token_required
@api_role_required(
    NombreRol.JEFE_SERVICIO,
    NombreRol.ALIMENTACION,
    NombreRol.COMEDOR,
)
def detalle(personal_id):
    """
    Proposito: Obtiene los datos de una persona por su identificador.
    Entrada: ID de personal en la URL.
    Salida: JSON con los datos de la persona solicitada.
    """
    personal = Personal.obtener_personal_por_id(personal_id)

    # Si no llega persona, devuelvo error
    if personal is None:
        raise NotFound("No existe la persona solicitada.")

    usuario = g.current_user
    tipo_personal = TipoPersonal.obtener_por_id(personal.tipo_personal_id)

    if usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value:
        es_residente = tipo_personal is not None and tipo_personal.nombre == "Residente"
        pertenece_a_su_sector = (
            usuario.sector_id is not None
            and personal.sector_id == usuario.sector_id
        )
        if not (es_residente or pertenece_a_su_sector):
            raise Forbidden("No tenés permiso para consultar esta persona.")

    sector = (
        Sector.obtener_por_id(personal.sector_id)
        if personal.sector_id is not None
        else None
    )
    tipo_menu = TipoMenu.obtener_por_id(personal.menu_id)

    resultado = personal_salida_schema.dump(
        {
            "id": personal.id,
            "dni": personal.dni,
            "nombre": personal.nombre,
            "apellido": personal.apellido,
            "tipo_personal": tipo_personal,
            "sector": sector,
            "tipo_menu": tipo_menu,
            "activo": personal.activo,
        }
    )
    return jsonify(resultado), 200


# ● GET /api/sectors/{sector_id}/personnel — listar el personal
@personal_sector_api_bp.get("/<int:sector_id>/personnel")
@token_required
@api_role_required(
    NombreRol.JEFE_SERVICIO,
    NombreRol.ALIMENTACION,
    NombreRol.COMEDOR,
)
def listar_por_sector(sector_id):
    """
    Proposito: Lista el personal activo que pertenece a un sector.
    Entrada: ID del sector en la URL; fecha, pagina y cantidad por pagina opcionales.
    Salida: JSON con el personal activo y la informacion de paginacion.
    """
    usuario = g.current_user
    parametros = personal_sector_query_schema.load(request.args)

    # El Jefe solo puede consultar el sector asignado a su usuario.
    if (
        usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value
        and usuario.sector_id != sector_id
    ):
        raise Forbidden("Un Jefe de Servicio solo puede consultar su propio sector.")

    sector = Sector.obtener_por_id(sector_id)
    if sector is None:
        raise NotFound("No existe el sector solicitado.")

    # El modelo no conserva historial de asignaciones; fecha se valida pero se usa
    # el sector_id actual de Personal para obtener los miembros activos.
    fecha = None 

    if parametros["fecha"] is not None:
        fecha = parametros["fecha"]
    else:
        fecha = datetime.now(timezone.utc) #se deja la validacion pero no se usa

    filtros = FiltrosPersonal(
        sector_id=sector_id,
        activo=True,
        pagina=parametros["pagina"],
        por_pagina=parametros["por_pagina"],
        fecha=fecha #Si no viene la fecha, se pone por defecto la fecha de hoy
    )
    resultados, total = Personal.buscar(filtros)

    personal_listado = [
        personal_salida_schema.dump(
            {
                "id": personal.id,
                "dni": personal.dni,
                "nombre": personal.nombre,
                "apellido": personal.apellido,
                "tipo_personal": {
                    "id": personal.tipo_personal_id,
                    "nombre": tipo_personal_nombre,
                },
                "sector": {
                    "id": personal.sector_id,
                    "nombre": sector_nombre,
                },
                "tipo_menu": {
                    "id": personal.menu_id,
                    "nombre": tipo_menu_nombre,
                },
                "activo": personal.activo,
            }
        )
        for personal, tipo_personal_nombre, sector_nombre, tipo_menu_nombre in resultados
    ]
    return (
        jsonify(
            {
                "data": personal_listado,
                "total": total,
                "page": filtros.pagina,
                "per_page": filtros.por_pagina,
            }
        ),
        200,
    )


@personal_api_bp.post("")
@token_required
@api_role_required(
    NombreRol.JEFE_SERVICIO,
    NombreRol.ALIMENTACION,
)
def crear():
    """
    Proposito: Crea una persona nueva.
    Entrada: JSON con DNI, nombre, apellido, tipo de personal, tipo de menu
    y sector cuando corresponda.
    Salida: JSON con los datos de la persona creada.
    """
    usuario = g.current_user
    datos = personal_entrada_schema.load(request.get_json())
    tipo_personal = TipoPersonal.obtener_por_id(datos["tipo_personal_id"])
    tipo_menu = TipoMenu.obtener_por_id(datos["menu_id"])

    if (
        Personal.obtener_por_dni(datos["dni"]) is not None
    ):  # si obtengo una persona con ese dni, excepcion
        raise Conflict("Ya existe una persona con ese DNI")

    if tipo_personal is None:  # si el id del tipo personal no existe, excepcion
        raise ValidationError({"tipo_personal_id": ["El tipo de personal no existe."]})

    if tipo_menu is None:  # si el id del tipo menu no existe, excepcion
        raise ValidationError({"menu_id": ["El tipo de menú no existe."]})

    es_jefe = (
        usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value
    )  # tomo si el usuario es jefe de servicio
    es_residente = (
        tipo_personal.nombre == "Residente"
    )  # tomo si la persona a crear es residente

    if es_jefe:
        if es_residente:
            raise Forbidden("Un Jefe de Servicio no puede crear Residentes.")
        if usuario.sector_id is None:
            raise Forbidden("El Jefe de Servicio no tiene un sector asignado.")
        datos["sector_id"] = usuario.sector_id
    elif es_residente:
        datos["sector_id"] = None
    elif datos.get("sector_id") is None:
        raise ValidationError(
            {"sector_id": ["El sector es obligatorio para Personal Fijo."]}
        )

    if datos.get("sector_id") is not None:
        sector = Sector.obtener_por_id(datos["sector_id"])
        if sector is None:
            raise ValidationError({"sector_id": ["El sector no existe."]})
        if not sector.activo:
            raise ValidationError({"sector_id": ["El sector no está activo."]})

    nuevo_personal = Personal.crear_personal(datos)
    sector = (
        Sector.obtener_por_id(nuevo_personal.sector_id)
        if nuevo_personal.sector_id is not None
        else None
    )
    resultado = personal_salida_schema.dump(
        {
            "id": nuevo_personal.id,
            "dni": nuevo_personal.dni,
            "nombre": nuevo_personal.nombre,
            "apellido": nuevo_personal.apellido,
            "tipo_personal": tipo_personal,
            "sector": sector,
            "tipo_menu": tipo_menu,
            "activo": nuevo_personal.activo,
        }
    )
    return jsonify(resultado), 201


@personal_api_bp.put("/<int:personal_id>")
@token_required
@api_role_required(
    NombreRol.JEFE_SERVICIO,
    NombreRol.ALIMENTACION,
)
def modificar(personal_id):
    """
    Proposito: Modifica los datos de una persona existente.
    Entrada: ID de personal en la URL y JSON con los datos actualizados;
    activo es opcional y permite activar o desactivar a la persona.
    Salida: JSON con los datos de la persona modificada.
    """
    usuario = g.current_user
    datos = personal_actualizacion_schema.load(request.get_json())

    persona_actual = Personal.obtener_personal_por_id(personal_id)
    if persona_actual is None:
        raise NotFound("No existe la persona solicitada.")

    tipo_personal = TipoPersonal.obtener_por_id(datos["tipo_personal_id"])
    if tipo_personal is None:
        raise ValidationError({"tipo_personal_id": ["El tipo de personal no existe."]})

    tipo_menu = TipoMenu.obtener_por_id(datos["menu_id"])
    if tipo_menu is None:
        raise ValidationError({"menu_id": ["El tipo de menú no existe."]})

    persona_con_dni = Personal.obtener_por_dni(datos["dni"])
    if persona_con_dni is not None and persona_con_dni.id != persona_actual.id:
        raise Conflict("El DNI ya corresponde a otra persona.")

    tipo_actual = TipoPersonal.obtener_por_id(persona_actual.tipo_personal_id)
    if tipo_actual is None:
        raise ValidationError(
            {"tipo_personal_id": ["El tipo actual de personal no existe."]}
        )

    es_jefe = usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value
    es_residente = tipo_personal.nombre == "Residente"

    if es_jefe:
        if tipo_actual.nombre == "Residente" or es_residente:
            raise Forbidden("Un Jefe de Servicio no puede modificar Residentes.")
        if usuario.sector_id is None:
            raise Forbidden("El Jefe de Servicio no tiene un sector asignado.")
        if persona_actual.sector_id != usuario.sector_id:
            raise Forbidden("Solo puede modificar personal de su propio sector.")
        if (
            datos.get("sector_id") is not None
            and datos["sector_id"] != usuario.sector_id
        ):
            raise Forbidden("No puede trasladar personal a otro sector.")
        datos["sector_id"] = usuario.sector_id
    elif es_residente:
        datos["sector_id"] = None
    elif datos.get("sector_id") is None:
        raise ValidationError(
            {"sector_id": ["El sector es obligatorio para Personal Fijo."]}
        )

    if datos.get("sector_id") is not None:
        sector = Sector.obtener_por_id(datos["sector_id"])
        if sector is None:
            raise ValidationError({"sector_id": ["El sector no existe."]})
        if not sector.activo:
            raise ValidationError({"sector_id": ["El sector no está activo."]})

    persona_actualizada = Personal.actualizar_personal(personal_id, datos)
    sector = (
        Sector.obtener_por_id(persona_actualizada.sector_id)
        if persona_actualizada.sector_id is not None
        else None
    )
    resultado = personal_salida_schema.dump(
        {
            "id": persona_actualizada.id,
            "dni": persona_actualizada.dni,
            "nombre": persona_actualizada.nombre,
            "apellido": persona_actualizada.apellido,
            "tipo_personal": tipo_personal,
            "sector": sector,
            "tipo_menu": tipo_menu,
            "activo": persona_actualizada.activo,
        }
    )
    return jsonify(resultado), 200


@personal_api_bp.delete("/<int:personal_id>")
@token_required
@api_role_required(NombreRol.JEFE_SERVICIO, NombreRol.ALIMENTACION)
def eliminar(personal_id):
    """
    Proposito: Elimina o desactiva una persona.
    Entrada: ID de personal en la URL.
    Salida: Confirmacion de la operacion realizada.
    """
    usuario = g.current_user
    personal_eliminar = Personal.obtener_personal_por_id(personal_id)
    if personal_eliminar is None:
        raise NotFound("No existe la persona solicitada.")

    es_jefe = usuario.rol.nombre == NombreRol.JEFE_SERVICIO.value
    if es_jefe:
        tipo_personal = TipoPersonal.obtener_por_id(personal_eliminar.tipo_personal_id)
        if (
            tipo_personal is None
            or tipo_personal.nombre == "Residente"
            or personal_eliminar.sector_id != usuario.sector_id
        ):
            raise Forbidden(
                "El Jefe de Servicio solo puede eliminar personal fijo de su sector."
            )

    # Con historial se conserva la persona y se desactiva, sin historial se elimina.
    if Personal.tiene_historial(personal_id):
        Personal.marcar_como_inactivo(personal_id)
        return (
            jsonify(
                {
                    "message": "La persona tenia historial y fue marcada como inactiva.",
                    "activo": False,
                }
            ),
            200,
        )

    Personal.eliminar_personal(personal_id)
    return (
        jsonify(
            {
                "message": "La persona fue eliminada.",
                "eliminada": True,
            }
        ),
        200,
    )
