import logging
from datetime import date
from flask import Blueprint, g, jsonify, request
from src.core.entregas import Entrega, EntregaDetalle
from src.core.sectores import Sector
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.roles import NombreRol
from src.web.api.helpers import token_required, api_role_required
from datetime import datetime
from marshmallow import ValidationError
from types import SimpleNamespace
from src.web.schemas.entregas import (
    entrega_crear_schema,
    entrega_filtros_schema,
    entrega_resumen_filtros_schema,
)

logger = logging.getLogger(__name__)
entregas_api_bp = Blueprint("entregas_api",__name__,url_prefix="/api/deliveries")

authorized_meals_api_bp = Blueprint(
    "api_comidas_autorizadas", __name__, url_prefix="/api/authorized_meals"
)

entregas_api_bp = Blueprint(
    "entregas_api",
    __name__,
    url_prefix="/api/deliveries",
)


# =========================================================
# GET /api/deliveries
# =========================================================

@entregas_api_bp.get("")
@token_required
@api_role_required(
    NombreRol.COMEDOR,
    NombreRol.ALIMENTACION,
)
def listar_entregas():
    """Lista entregas aplicando filtros."""

    try:
        datos = entrega_filtros_schema.load(
            request.args.to_dict()
        )
    except ValidationError as error:
        return jsonify(
            error={
                "code": "validation_error",
                "fields": error.messages,
            }
        ), 400

    fecha = datos.get("fecha")
    sector_id = datos.get("sector_id")
    tipo_comida = datos.get("tipo_comida")

    usuario = g.current_user

    # Si es Sector Comedor y no manda fecha,
    # se muestran las entregas del día actual.
    if (
        usuario.rol.nombre == NombreRol.COMEDOR
        and fecha is None
    ):
        fecha = date.today()

    # Regla de negocio:
    # si se manda un sector debe existir.
    if sector_id is not None:
        sector = Sector.obtener_por_id(sector_id)

        if sector is None:
            return jsonify(
                error={
                    "code": "sector_not_found",
                    "message": "El sector no existe.",
                }
            ), 404

    paginacion = Entrega.buscar(
        fecha=fecha,
        sector_id=sector_id,
        tipo_comida=tipo_comida,
    )

    resultado = []

    for entrega in paginacion.items:
        resultado.append({
            "id": entrega.id,
            "fecha_hora": entrega.fecha_hora.isoformat(),
            "usuario_comedor_id": entrega.usuario_comedor_id,
            "responsable_retiro": entrega.responsable_retiro,
        })

    return jsonify({
        "data": resultado,
        "total": paginacion.total_items,
        "page": paginacion.page,
        "per_page": paginacion.per_page,
    }), 200


# =========================================================
# POST /api/deliveries
# =========================================================

@entregas_api_bp.post("")
@token_required
@api_role_required(NombreRol.COMEDOR)
def crear_entrega():
    """Registra una nueva entrega."""

    usuario = g.current_user

    try:
        datos = entrega_crear_schema.load(
            request.get_json(silent=True) or {}
        )
    except ValidationError as error:
        return jsonify(
            error={
                "code": "validation_error",
                "fields": error.messages,
            }
        ), 400

    responsable_retiro = datos["responsable_retiro"]
    tipo_comida = datos["tipo_comida"]
    personas = datos["personas"]

    detalles_validados = []
    personas_recibidas = set()

    for item in personas:
        person_id = item["person_id"]
        tipo_menu_entregado_id = item[
            "tipo_menu_entregado_id"
        ]

        # Regla de negocio:
        # una persona no debe aparecer dos veces
        # dentro de la misma entrega.
        if person_id in personas_recibidas:
            return jsonify(
                error={
                    "code": "duplicated_person",
                    "message":
                        f"La persona {person_id} "
                        "está repetida en la entrega.",
                }
            ), 400

        personas_recibidas.add(person_id)

        # Buscar una solicitud autorizada
        # para esa persona, comida y fecha.
        solicitud = (
            SolicitudDetalle
            .obtener_autorizada_para_entrega(
                person_id=person_id,
                tipo_comida=tipo_comida,
                fecha=date.today(),
            )
        )

        if solicitud is None:
            return jsonify(
                error={
                    "code": "authorization_not_found",
                    "message":
                        f"La persona {person_id} "
                        f"no tiene autorización vigente "
                        f"para {tipo_comida} "
                        "en la fecha actual.",
                }
            ), 400

        # El menú entregado debe coincidir
        # con el menú que fue autorizado.
        if solicitud.tipo_menu_id != tipo_menu_entregado_id:
            return jsonify(
                error={
                    "code": "invalid_menu",
                    "message":
                        f"El menú entregado para la persona "
                        f"{person_id} no coincide con "
                        "el menú autorizado.",
                }
            ), 400

        # Una solicitud autorizada no puede
        # entregarse más de una vez.
        if EntregaDetalle.existe_por_solicitud(
            solicitud.id
        ):
            return jsonify(
                error={
                    "code": "already_delivered",
                    "message":
                        f"La comida de la persona "
                        f"{person_id} ya fue entregada.",
                }
            ), 409

        detalles_validados.append({
            "solicitud_detalle_id": solicitud.id,
            "tipo_menu_entregado_id":
                tipo_menu_entregado_id,
        })

    try:
        entrega = Entrega.crear_con_detalles(
            usuario_comedor_id=usuario.id,
            responsable_retiro=responsable_retiro,
            detalles=detalles_validados,
        )

    except Exception:
        logger.exception(
            "Error al registrar una entrega."
        )

        return jsonify(
            error={
                "code": "internal_error",
                "message":
                    "Ocurrió un error al registrar la entrega.",
            }
        ), 500

    logger.info(
        "Entrega %s registrada por usuario %s",
        entrega.id,
        usuario.id,
    )

    return jsonify({
        "id": entrega.id,
        "fecha_hora": entrega.fecha_hora.isoformat(),
        "tipo_comida": tipo_comida,
        "usuario_comedor": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "email": usuario.email,
        },
        "responsable_retiro":
            entrega.responsable_retiro,
        "personas": [
            {
                "person_id": item["person_id"],
                "tipo_menu_entregado_id":
                    item["tipo_menu_entregado_id"],
            }
            for item in personas
        ],
    }), 201


# =========================================================
# GET /api/deliveries/summary
# =========================================================

@entregas_api_bp.get("/summary")
@token_required
@api_role_required(
    NombreRol.COMEDOR,
    NombreRol.ALIMENTACION,
)
def resumen_entregas():
    """Obtiene autorizadas vs entregadas."""

    try:
        datos = entrega_resumen_filtros_schema.load(
            request.args.to_dict()
        )
    except ValidationError as error:
        return jsonify(
            error={
                "code": "validation_error",
                "fields": error.messages,
            }
        ), 400

    fecha = datos.get("fecha")
    sector_id = datos.get("sector_id")
    tipo_comida = datos.get("tipo_comida")

    if sector_id is not None:
        sector = Sector.obtener_por_id(sector_id)

        if sector is None:
            return jsonify(
                error={
                    "code": "sector_not_found",
                    "message": "El sector no existe.",
                }
            ), 404

    try:
        resumen = Entrega.obtener_resumen(
            fecha=fecha,
            sector_id=sector_id,
            tipo_comida=tipo_comida,
        )

    except Exception:
        logger.exception(
            "Error al obtener resumen de entregas."
        )

        return jsonify(
            error={
                "code": "internal_error",
                "message":
                    "Ocurrió un error al obtener "
                    "el resumen de entregas.",
            }
        ), 500

    return jsonify(resumen), 200


# =========================================================
# GET /api/deliveries/{delivery_id}
# =========================================================

@entregas_api_bp.get("/<int:delivery_id>")
@token_required
@api_role_required(
    NombreRol.COMEDOR,
    NombreRol.ALIMENTACION,
)
def detalle_entrega(delivery_id):
    """Obtiene el detalle completo de una entrega."""

    entrega = Entrega.obtener_por_id(delivery_id)

    if entrega is None:
        return jsonify(
            error={
                "code": "delivery_not_found",
                "message": "La entrega no existe.",
            }
        ), 404

    detalles = []

    for detalle in entrega.detalles:
        detalles.append({
            "id": detalle.id,
            "solicitud_detalle_id":
                detalle.solicitud_detalle_id,
            "person_id":
                detalle.solicitud_detalle.person_id,
            "tipo_comida":
                detalle.solicitud_detalle.tipo_comida,
            "tipo_menu_entregado_id":
                detalle.tipo_menu_entregado_id,
        })

    return jsonify({
        "id": entrega.id,
        "fecha_hora": entrega.fecha_hora.isoformat(),
        "usuario_comedor_id":
            entrega.usuario_comedor_id,
        "responsable_retiro":
            entrega.responsable_retiro,
        "detalles": detalles,
    }), 200


## =============== COMIDAS AUTORIZADAS =============== ##
@authorized_meals_api_bp.get("/")
def listar_comidas_autorizadas():
    """
    Proposito: Lista comidas autorizadas para el usuario autenticado.
    Entrada: Query parameters para filtrar comidas por fecha, dni, nombre y apellido, sector y tipo de comida
    Salida: JSON con listado de comidas autorizadas
    """
    usuario = g.api_user
    roles_permitidos = {
        NombreRol.COMEDOR.value,
        NombreRol.ALIMENTACION.value,
        NombreRol.ADMINISTRADOR.value,
    }

    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify(
                {"error": "El rol del usuario no puede consultar comidas autorizadas."}
            ),
            403,
        )
    # tipos de query parameters para filtrado fecha/dni/nombre y apellido/sector/tipo de comida
    args = request.args
    print(args)
    if not args:
        return (
            jsonify(
                {
                    "error": "Se requieren parámetros de consulta para filtrar comidas autorizadas."
                }
            ),
            400,
        )
    # aplicar filtrado a la consulta SQL para obtener comidas autorizadas según los args
    # TODO cumplir reglas de negocio para este endpoint: pedidos en estado autorizado, indicar cuanto ya fue entregado
    # comidas_autorizadas = .obtener_comidas_autorizadas()
    comida = SimpleNamespace(
        id="1",
        nombre="Pollo a la plancha",
        descripcion="Pollo a la plancha con ensalada",
        activo=True,
        fecha_creacion=datetime.now(),
        fecha_modificacion=datetime.now(),
    )
    comidas_autorizadas = [comida]
    return (
        jsonify(
            [
                {
                    "id": comida.id,
                    "nombre": comida.nombre,
                    "descripcion": comida.descripcion,
                    "activo": comida.activo,
                    "fecha_creacion": comida.fecha_creacion,
                    "fecha_modificacion": comida.fecha_modificacion,
                }
                for comida in comidas_autorizadas
            ]
        ),
        200,
    )


@authorized_meals_api_bp.get("/<int:person_id>")
def obtener_comida_autorizada(person_id):
    """
    Proposito: Obtiene la comida autorizada correspondiente a un ID de persona
    Entrada: ID de persona y query parameter fecha
    Salida: JSON con listado de comidas autorizadas correspondientes a la persona y fecha
    """
    usuario = g.api_user
    roles_permitidos = {
        NombreRol.COMEDOR.value,
        NombreRol.ALIMENTACION.value,
        NombreRol.ADMINISTRADOR.value,
    }

    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify(
                {"error": "El rol del usuario no puede consultar comidas autorizadas."}
            ),
            403,
        )
    fecha_comida = request.args.get("fecha")
    if not fecha_comida:
        fecha_comida = datetime.now().date()
    # persona = Personal.obtener_personal_por_id(person_id)
    # if not persona:
    #     abort(404, description="No existe la persona solicitada")
    # TODO cumplir reglas de negocio para este endpoint
    # comidas_autorizadas = .obtener_comidas_autorizadas_por_persona(person_id, fecha_comida)
    comidas_autorizadas = [
        SimpleNamespace(
            id="1",
            nombre="Pollo a la plancha",
            descripcion="Pollo a la plancha con ensalada",
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now(),
        ),
        SimpleNamespace(
            id="2",
            nombre="Pasta al pesto",
            descripcion="Pasta al pesto con ensalada",
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now(),
        ),
    ]
    if not comidas_autorizadas:
        return (
            jsonify({"error": "No existe la comida autorizada solicitada"}),
            404,
        )
    return (
        jsonify(
            [
                {
                    "id": comida.id,
                    "nombre": comida.nombre,
                    "descripcion": comida.descripcion,
                    "activo": comida.activo,
                    "fecha_creacion": comida.fecha_creacion,
                    "fecha_modificacion": comida.fecha_modificacion,
                }
                for comida in comidas_autorizadas
            ]
        ),
        200,
    )