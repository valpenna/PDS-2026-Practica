from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError

from src.core.configuracion import Configuracion
from src.core.pedidos import FiltrosPedido, Pedido, PedidoYaResuelto, SolicitudesInvalidas
from src.core.personal import Personal
from src.core.roles import NombreRol
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.tipos_menu import TipoMenu
from src.core.usuarios import User
from src.web.api.helpers import api_role_required, token_required
from src.web.schemas.autorizaciones import autorizaciones_filtros_schema, autorizar_pedido_schema


autorizaciones_api_bp = Blueprint(
    "api_autorizaciones", __name__, url_prefix="/api/authorizations"
)


@autorizaciones_api_bp.get("")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def listar_autorizaciones():
    try:
        datos = autorizaciones_filtros_schema.load(request.args.to_dict())
    except ValidationError as error:
        return jsonify(error={"code": "validation_error", "fields": error.messages}), 422

    filtros = FiltrosPedido(
        fecha_desde=datos.get("fecha_desde"),
        fecha_hasta=datos.get("fecha_hasta"),
        sector_id=datos.get("sector_id"),
        tipo_comida=datos.get("tipo_comida"),
        tipo_menu_id=datos.get("tipo_menu_id"),
        estado=datos.get("estado"),
        pagina=datos["page"],
        por_pagina=Configuracion.obtener().elementos_por_pagina,
    )
    pedidos, total = Pedido.buscar(filtros)
    respuesta = []
    for pedido in pedidos:
        creado_por = User.obtener_por_id(pedido.created_by_id)
        solicitudes = SolicitudDetalle.obtener_por_pedido(pedido.id)
        cantidad_pedida = 0
        cantidad_autorizada = 0

        for detalle in solicitudes:
            if filtros.tipo_comida is not None and detalle.tipo_comida != filtros.tipo_comida:
                continue
            if filtros.tipo_menu_id is not None and detalle.tipo_menu_id != filtros.tipo_menu_id:
                continue

            cantidad_pedida += 1
            if detalle.estado_autorizacion == "autorizado":
                cantidad_autorizada += 1

        respuesta.append({
            "id": pedido.id,
            "sector_id": pedido.sector_id,
            "fecha": pedido.fecha.isoformat(),
            "estado": pedido.estado,
            "created_by_id": pedido.created_by_id,
            "creado_por": {
                "nombre": creado_por.nombre,
                "apellido": creado_por.apellido,
                "dni": creado_por.dni,
            },
            "fecha_creacion": pedido.fecha_creacion.isoformat(),
            "cantidad_pedida": cantidad_pedida,
            "cantidad_autorizada": cantidad_autorizada,
        })

    return jsonify({
        "data": respuesta,
        "total": total,
        "page": filtros.pagina,
        "per_page": filtros.por_pagina,
    }), 200


@autorizaciones_api_bp.get("/<int:request_id>")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def obtener_autorizacion(request_id):
    pedido = Pedido.obtener_por_id(request_id)
    if pedido is None:
        return jsonify(error={
            "code": "request_not_found",
            "message": "El pedido solicitado no existe.",
        }), 404
    return jsonify(_serializar_pedido(pedido)), 200


@autorizaciones_api_bp.put("/<int:request_id>")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def autorizar_pedido(request_id):
    try:
        datos = autorizar_pedido_schema.load(request.get_json(silent=True))
    except ValidationError as error:
        return jsonify(error={"code": "validation_error", "fields": error.messages}), 400

    try:
        pedido = Pedido.autorizar(request_id, datos["solicitudes"], g.current_user.id)
    except PedidoYaResuelto as error:
        return jsonify(error={"code": "request_conflict", "message": str(error)}), 409
    except SolicitudesInvalidas as error:
        return jsonify(error={"code": "invalid_requests", "message": str(error)}), 400

    if pedido is None:
        return jsonify(error={
            "code": "request_not_found",
            "message": "El pedido solicitado no existe.",
        }), 404
    return jsonify(_serializar_pedido(pedido)), 200


def _serializar_pedido(pedido):
    creado_por = User.obtener_por_id(pedido.created_by_id)
    detalle = {tipo_comida: {} for tipo_comida in ("almuerzo", "desayuno", "merienda", "cena")}
    cantidad_autorizada = 0
    solicitudes = SolicitudDetalle.obtener_por_pedido(pedido.id)

    for solicitud in solicitudes:
        menu = TipoMenu.obtener_por_id(solicitud.tipo_menu_id)
        nombre_menu = menu.nombre.lower()
        menus = detalle[solicitud.tipo_comida]
        if nombre_menu not in menus:
            menus[nombre_menu] = {
                "tipo_comida": solicitud.tipo_comida,
                "tipo_menu_id": solicitud.tipo_menu_id,
                "menu": menu.nombre,
                "pedida": 0,
                "autorizada": 0,
                "personas": [],
            }

        grupo = menus[nombre_menu]
        grupo["pedida"] += 1
        if solicitud.estado_autorizacion == "autorizado":
            grupo["autorizada"] += 1
            cantidad_autorizada += 1

        persona = Personal.obtener_personal_por_id(solicitud.person_id)
        grupo["personas"].append({
            "id": solicitud.id,
            "person_id": solicitud.person_id,
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "condicion": solicitud.condicion,
            "estado_autorizacion": solicitud.estado_autorizacion,
        })

    return {
        "id": pedido.id,
        "sector_id": pedido.sector_id,
        "fecha": pedido.fecha.isoformat(),
        "estado": pedido.estado,
        "created_by_id": pedido.created_by_id,
        "creado_por": {
            "nombre": creado_por.nombre,
            "apellido": creado_por.apellido,
        },
        "fecha_creacion": pedido.fecha_creacion.isoformat(),
        "cantidad_pedida": len(solicitudes),
        "cantidad_autorizada": cantidad_autorizada,
        "detalle": detalle,
    }