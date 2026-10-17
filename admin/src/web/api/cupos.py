from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, NotFound

from src.core.configuracion import Configuracion
from src.core.cupos import Cupo, CupoDuplicado, FiltrosCupo, SectorCupoInvalido
from src.core.roles import NombreRol
from src.web.api.helpers import api_role_required, token_required
from src.web.schemas.cupos import cupo_crear_schema, cupo_detalle_schema, cupo_filtros_schema, cupo_listado_schema, cupo_salida_schema


cupos_api_bp = Blueprint("api_cupos", __name__, url_prefix="/api/quotas")


def resolver_sector_consulta(sector_id):
    """Restringe la consulta al sector asignado si el usuario es jefe de servicio.

    Devuelve el sector permitido y una respuesta 403 si el acceso está prohibido.
    """
    if g.current_user.rol.nombre == NombreRol.JEFE_SERVICIO:
        sector_propio = g.current_user.sector_id
        if sector_propio is None or (sector_id is not None and sector_id != sector_propio):
            return None, (jsonify(error={"code": "forbidden", "message": "Solo podés consultar cupos de tu sector asignado."}), 403)
        return sector_propio, None
    return sector_id, None


@cupos_api_bp.get("")
@token_required
@api_role_required(NombreRol.ALIMENTACION, NombreRol.JEFE_SERVICIO, NombreRol.COMEDOR)
def listar():
    """Lista los cupos filtrados y paginados del sector permitido."""
    datos = cupo_filtros_schema.load(request.args.to_dict())
    sector_id, respuesta_error = resolver_sector_consulta(datos.get("sector_id"))
    if respuesta_error is not None:
        return respuesta_error

    limite = Configuracion.obtener().elementos_por_pagina
    filtros = FiltrosCupo(
        sector_id=sector_id,
        tipo_comida=datos.get("tipo_comida"),
        orden=datos["sort"],
        pagina=datos["page"],
        por_pagina=limite,
    )
    cupos, total = Cupo.buscar(filtros)
    return jsonify({
        "data": cupo_listado_schema.dump(cupos),
        "total": total,
        "page": filtros.pagina,
        "per_page": filtros.por_pagina,
    }), 200


@cupos_api_bp.get("/<int:cupo_id>")
@token_required
@api_role_required(NombreRol.ALIMENTACION, NombreRol.JEFE_SERVICIO, NombreRol.COMEDOR)
def detalle(cupo_id):
    """Devuelve el detalle de un cupo si el usuario puede consultar su sector."""
    cupo = Cupo.obtener_por_id(cupo_id)
    if cupo is None:
        raise NotFound("El cupo solicitado no existe.")

    _, respuesta_error = resolver_sector_consulta(cupo.sector_id)
    if respuesta_error is not None:
        return respuesta_error
    return jsonify(cupo_detalle_schema.dump(cupo)), 200


@cupos_api_bp.post("")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def crear():
    """Crea un cupo a partir del JSON validado y devuelve su representación."""
    try:
        contenido = request.get_json()
    except BadRequest:
        return jsonify(error={"code": "validation_error", "message": "El JSON no es válido."}), 400

    datos = cupo_crear_schema.load(contenido)
    cupo = Cupo.crear(**datos)
    return jsonify(cupo_salida_schema.dump(cupo)), 201


@cupos_api_bp.put("/<int:cupo_id>")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def actualizar(cupo_id):
    """Actualiza un cupo existente con el JSON validado y devuelve el resultado."""
    cupo = Cupo.obtener_por_id(cupo_id)
    if cupo is None:
        raise NotFound("El cupo solicitado no existe.")

    contenido = request.get_json()
    datos = cupo_crear_schema.load(contenido)
    cupo.actualizar(**datos)
    return jsonify(cupo_salida_schema.dump(cupo)), 200


@cupos_api_bp.delete("/<int:cupo_id>")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def eliminar(cupo_id):
    """Elimina un cupo existente y devuelve una respuesta sin contenido."""
    cupo = Cupo.obtener_por_id(cupo_id)
    if cupo is None:
        raise NotFound("El cupo solicitado no existe.")

    cupo.eliminar()
    return "", 204



@cupos_api_bp.errorhandler(ValidationError)
def datos_invalidos(error):
    """Devuelve los errores de validación con el estado según el método HTTP."""
    estado = 400 if request.method in {"POST", "PUT"} else 422
    return jsonify(error={"code": "validation_error", "fields": error.messages}), estado


@cupos_api_bp.errorhandler(NotFound)
def cupo_no_encontrado(error):
    """Devuelve un error 404 cuando el cupo solicitado no existe."""
    return jsonify(error={"code": "quota_not_found", "message": error.description}), 404


@cupos_api_bp.errorhandler(SectorCupoInvalido)
def sector_invalido(error):
    """Devuelve un error 400 cuando el sector no es válido para un cupo."""
    return jsonify(error={"code": "invalid_sector", "message": str(error)}), 400


@cupos_api_bp.errorhandler(CupoDuplicado)
def cupo_duplicado(error):
    """Devuelve un error 400 cuando ya existe el cupo solicitado."""
    return jsonify(error={"code": "quota_exists", "message": str(error)}), 400


@cupos_api_bp.errorhandler(IntegrityError)
def cupo_conflictivo(error):
    """Devuelve el conflicto de integridad según la operación solicitada."""
    if request.method == "DELETE":
        return jsonify(error={"code": "quota_conflict", "message": "No se pudo eliminar el cupo porque otros registros lo referencian."}), 409
    accion = "modificar" if request.method == "PUT" else "crear"
    return jsonify(error={"code": "quota_conflict", "message": f"No se pudo {accion} el cupo. Revisá el sector y el tipo de comida."}), 400