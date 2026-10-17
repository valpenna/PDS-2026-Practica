from functools import wraps
from types import SimpleNamespace
from datetime import datetime
from flask import Blueprint, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException
from datetime import datetime, timedelta
from src.core.roles import NombreRol
from src.core.sectores import Sector
from src.core.usuarios import User
from src.core.pedidos import Pedido
from src.core.personal import Personal
from src.web.api.helpers import token_required
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.tipos_menu import TipoMenu
from src.core.cupos import Cupo
import calendar

pedidos_api_bp = Blueprint("api_pedidos", __name__, url_prefix="/api/requests")


@pedidos_api_bp.errorhandler(HTTPException)
def _error_http_api(error):
    return (
        jsonify(
            error={
                "status": error.code,
                "detail": error.description,
            }
        ),
        error.code,
    )


@pedidos_api_bp.get("/")
@token_required
def listar_pedidos():
    """
    Proposito: Lista pedidos, según el filtro solicitado.
    Entrada: Query parameters rango de fechas, tipo de comida, tipo de menu, estado(C/A/R); paginacion
    Salida: listado paginado de pedidos con sus totales por comida y tipo de menú.
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar sectores."}),
            403,
        )
    # TODO filtros por query
    pedidos = Pedido.obtener_por_sector(usuario.sector_id)
    for pedido in pedidos:
        solicitudes_del_pedido = SolicitudDetalle.obtener_por_pedido(pedido.id)
        contadores_tc = {"desayuno": 0, "almuerzo": 0, "merienda": 0, "cena": 0}
        contadores_tm = {}
        menus = TipoMenu.obtener_todos()
        for menu in menus:
            contadores_tm[menu.nombre] = 0
        for solicitud in solicitudes_del_pedido:
            menu_solicitado = TipoMenu.obtener_por_id(solicitud.tipo_menu_id)
            contadores_tm[menu_solicitado.nombre] += 1
            tipo_comida = solicitud.tipo_comida.lower()
            contadores_tc[tipo_comida] += 1
        respuesta = []
        creado_por = User.obtener_por_id(pedido.created_by_id)
        respuesta.append(
            {
                "id": pedido.id,
                "sector_id": pedido.sector_id,
                "fecha": pedido.fecha,
                "estado": pedido.estado,
                "created_by_id": pedido.created_by_id,
                "creado_por": {
                    "email": creado_por.email,
                    "nombre": creado_por.nombre,
                    "apellido": creado_por.apellido,
                    "dni": creado_por.dni,
                },
                "fecha_creacion": pedido.fecha_creacion,
                "contadores_menus": contadores_tm,
                "contadores_tc": contadores_tc,
            }
        )

    return jsonify(respuesta), 200


@pedidos_api_bp.get("/<int:request_id>")
@token_required
def obtener_pedido(request_id):
    """
    Proposito: Obtiene el pedido correspondiente a un ID
    Entrada: ID de pedido
    Salida: JSON detalle completo del pedido — cantidades pedidas por comida y tipo de menú, personas incluidas, estado; si ya fue revisado por Servicio de Alimentación, incluir también las cantidades autorizadas como referencia de solo lectura, sin mezclarlas con las pedidas.
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar sectores."}),
            401,
        )
    pedido = Pedido.obtener_por_id(request_id)
    if not pedido:
        return (
            jsonify({"error": "No existe el pedido solicitado."}),
            404,
        )
    if pedido.sector_id != usuario.sector_id:
        return (
            jsonify({"error": "El pedido no pertenece a tu sector."}),
            403,
        )
    user_creador = User.obtener_por_id(pedido.created_by_id)
    solicitudes_del_pedido = SolicitudDetalle.obtener_por_pedido(pedido.id)
    actores = []
    contadores_tc = {"desayuno": 0, "almuerzo": 0, "merienda": 0, "cena": 0}
    contadores_tm = {}
    menus = TipoMenu.obtener_todos()
    for menu in menus:
        contadores_tm[menu.nombre] = 0
    estado_solicitudes = {"pendiente": 0, "autorizado": 0, "rechazado": 0}
    total_pedidos = len(solicitudes_del_pedido)
    for solicitud in solicitudes_del_pedido:
        menu_solicitado = TipoMenu.obtener_por_id(solicitud.tipo_menu_id)
        contadores_tm[menu_solicitado.nombre] += 1
        tipo_comida = solicitud.tipo_comida.lower()
        contadores_tc[tipo_comida] += 1
        estado_solicitudes[solicitud.estado_autorizacion] += 1
        actores.append(
            {
                "personal": {
                    "dni": solicitud.person_dni_snapshot,
                    "id": solicitud.person_id,
                    "nombre": solicitud.person_nombre_snapshot,
                    "apellido": solicitud.person_apellido_snapshot,
                    "tipo_personal_id": solicitud.tipo_personal_id_snapshot,
                    "sector_id": solicitud.sector_id_snapshot,
                    "menu_id": solicitud.tipo_menu_id,
                    "activo": solicitud.activo_snapshot,
                },
                "tipo_comida": solicitud.tipo_comida,
                "tipo_menu_id": solicitud.tipo_menu_id,
                "condicion": solicitud.condicion,
                "estado_autorizacion": solicitud.estado_autorizacion,
            }
        )
    return (
        jsonify(
            {
                "id": pedido.id,
                "sector_id": pedido.sector_id,
                "fecha": pedido.fecha,
                "estado": pedido.estado,
                "created_by_id": pedido.created_by_id,
                "creado_por": {
                    "email": user_creador.email,
                    "nombre": user_creador.nombre,
                    "apellido": user_creador.apellido,
                    "dni": user_creador.dni,
                },
                "personal_solicitado": actores,
                "fecha_creacion": pedido.fecha_creacion,
                "contadores_menus": contadores_tm,
                "contadores_tc": contadores_tc,
                "autorizados": estado_solicitudes["autorizado"],
                "pendientes": estado_solicitudes["pendiente"],
                "rechazados": estado_solicitudes["rechazado"],
                "total_pedidos": total_pedidos,
            }
        ),
        200,
    )


@pedidos_api_bp.delete("/<int:request_id>")
@token_required
def eliminar_pedido(request_id):
    """
    Proposito: Elimina un pedido en base a su ID
    Entrada: ID de pedido
    Salida: Confirmacion
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.JEFE_SERVICIO.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar sectores."}),
            401,
        )
    pedido = Pedido.obtener_por_id(request_id)
    if not pedido:
        return (
            jsonify({"error": "El pedido no existe"}),
            404,
        )
    if pedido.sector_id != usuario.sector_id:
        return (
            jsonify(
                {"error": "El sector del pedido no corresponde al sector del jefe."}
            ),
            403,
        )
    if pedido.estado.lower() == "autorizado" or pedido.estado.lower() == "rechazado":
        return (jsonify({"error": f"El pedido ya fue {pedido.estado.lower()}"}), 409)

    estado = False
    eliminado = Pedido.eliminar(request_id)
    if eliminado:
        estado = True
    if estado:
        estado = "El pedido fue eliminado correctamente."
    else:
        estado = "El pedido no pudo ser eliminado."
    return jsonify({"estado": estado}), 200


def sumar_un_mes(fecha):
    """Devuelve la misma fecha del mes siguiente cuando sea posible."""
    if fecha.month == 12:
        anio = fecha.year + 1
        mes = 1
    else:
        anio = fecha.year
        mes = fecha.month + 1

    ultimo_dia = calendar.monthrange(anio, mes)[1]
    dia = min(fecha.day, ultimo_dia)

    return fecha.replace(year=anio, month=mes, day=dia)


def generar_fechas(periodicidad, fecha_desde, fecha_hasta):
    """General un array con fechas basandose en la periodicidad"""
    fechas = []
    fecha_actual = fecha_desde

    while fecha_actual <= fecha_hasta:
        fechas.append(fecha_actual)

        if periodicidad == "diaria":
            fecha_actual += timedelta(days=1)

        elif periodicidad == "semanal":
            fecha_actual += timedelta(weeks=1)

        elif periodicidad == "mensual":
            fecha_actual = sumar_un_mes(fecha_actual)

    return fechas


@pedidos_api_bp.post("")
@token_required
def crear_pedido():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "El cuerpo debe contener un JSON válido."}), 400

    usuario = g.current_user
    # Solo Jefe de Servicio
    if usuario.rol is None or usuario.rol.nombre != NombreRol.JEFE_SERVICIO.value:
        return jsonify({"error": "Solo un Jefe de Servicio puede crear pedidos."}), 403
    # El sector sale siempre del usuario autenticado
    sector_id = usuario.sector_id
    if sector_id is None:
        return (
            jsonify({"error": "El Jefe de Servicio no tiene un sector asignado."}),
            400,
        )
    periodicidad = data.get("periodicidad")
    fecha_desde_str = data.get("fecha_desde")
    fecha_hasta_str = data.get("fecha_hasta")
    detalles = data.get("detalles", [])
    if periodicidad not in {"diaria", "semanal", "mensual"}:
        return (
            jsonify({"error": "La periodicidad debe ser diaria, semanal o mensual."}),
            400,
        )
    if not fecha_desde_str or not fecha_hasta_str:
        return jsonify({"error": "fecha_desde y fecha_hasta son obligatorias."}), 400
    if not detalles:
        return (
            jsonify({"error": "Debe incluir al menos una persona en el pedido."}),
            400,
        )
    try:
        fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Las fechas deben tener formato YYYY-MM-DD."}), 400
    if fecha_hasta < fecha_desde:
        return (
            jsonify({"error": "fecha_hasta no puede ser anterior a fecha_desde."}),
            400,
        )
    fechas = generar_fechas(periodicidad, fecha_desde, fecha_hasta)
    # Primero valido todos los detalles
    detalles_validados = []
    for item in detalles:
        person_id = item.get("person_id")
        tipo_comida = item.get("tipo_comida")

        if not person_id or not tipo_comida:
            return (
                jsonify({"error": "Cada detalle debe tener person_id y tipo_comida."}),
                400,
            )

        if tipo_comida not in {"desayuno", "almuerzo", "merienda", "cena"}:
            return jsonify({"error": f"Tipo de comida inválido: {tipo_comida}."}), 400

        persona = Personal.obtener_personal_por_id(person_id)

        if persona is None:
            return jsonify({"error": f"No existe la persona {person_id}."}), 400

        if not persona.activo:
            return jsonify({"error": f"La persona {person_id} está inactiva."}), 400

        # Personal fijo tiene sector.
        # Residente tiene sector_id = None.
        if persona.sector_id is not None and persona.sector_id != sector_id:
            return (
                jsonify(
                    {
                        "error": f"La persona {person_id} no pertenece al sector del Jefe."
                    }
                ),
                400,
            )

        cupo = Cupo.obtener_por_sector_y_tipo_comida(sector_id, tipo_comida)

        if cupo is None:
            return (
                jsonify({"error": f"No existe cupo configurado para {tipo_comida}."}),
                400,
            )

        detalles_validados.append(
            {"persona": persona, "tipo_comida": tipo_comida, "cupo": cupo}
        )

    # Ahora genero un pedido por cada fecha
    pedidos_creados = []
    for fecha in fechas:
        # Necesitás un método de este estilo en Pedido
        # para cumplir el 409 pedido duplicado.
        pedido_existente = Pedido.obtener_por_sector_y_fecha(sector_id, fecha)
        if pedido_existente is not None:
            return (
                jsonify(
                    {
                        "error": f"Ya existe un pedido para el sector en la fecha {fecha}."
                    }
                ),
                409,
            )

        pedido = Pedido(
            sector_id=sector_id,
            fecha=fecha,
            estado="confirmado",
            created_by_id=usuario.id,
        )

        pedido.guardar()

        contadores = {"desayuno": 0, "almuerzo": 0, "merienda": 0, "cena": 0}

        personas_comidas = set()

        for item in detalles_validados:
            persona = item["persona"]
            tipo_comida = item["tipo_comida"]
            cupo = item["cupo"]
            clave = (persona.id, tipo_comida)
            # Evita repetir la misma persona/comida
            # dentro del mismo pedido
            if clave in personas_comidas:
                return (
                    jsonify(
                        {
                            "error": f"La persona {persona.id} está repetida "
                            f"para {tipo_comida}."
                        }
                    ),
                    400,
                )
            personas_comidas.add(clave)
            cantidad_actual = contadores[tipo_comida]
            if cantidad_actual < cupo.cantidad_comensales:
                condicion = "regular"
            else:
                condicion = "excepcion"

            detalle = SolicitudDetalle(
                pedido_id=pedido.id,
                person_id=persona.id,
                person_dni_snapshot=persona.dni,
                person_nombre_snapshot=persona.nombre,
                person_apellido_snapshot=persona.apellido,
                tipo_personal_id_snapshot=persona.tipo_personal_id,
                sector_id_snapshot=persona.sector_id,
                activo_snapshot=persona.activo,
                tipo_comida=tipo_comida,
                tipo_menu_id=persona.menu_id,
                condicion=condicion,
                estado_autorizacion="pendiente",
            )
            detalle.guardar()
            contadores[tipo_comida] += 1
        pedidos_creados.append({"pedido_id": pedido.id, "fecha": fecha.isoformat()})
    return (
        jsonify(
            {
                "mensaje": "Pedido creado correctamente.",
                "periodicidad": periodicidad,
                "pedidos": pedidos_creados,
            }
        ),
        201,
    )


@pedidos_api_bp.put("/<int:request_id>")
@token_required
def actualizar_pedido(request_id):
    usuario = g.current_user

    # 1. Solo Jefe de Servicio
    if usuario.rol is None or usuario.rol.nombre != NombreRol.JEFE_SERVICIO.value:
        return (
            jsonify({"error": "Solo un Jefe de Servicio puede modificar pedidos."}),
            403,
        )

    sector_id = usuario.sector_id

    # 2. Buscar pedido
    pedido = Pedido.obtener_por_id(request_id)

    if pedido is None:
        return jsonify({"error": "El pedido no existe."}), 404

    # 3. Tiene que ser de su sector
    if pedido.sector_id != sector_id:
        return jsonify({"error": "El pedido no pertenece al sector del Jefe."}), 403

    # 4. Solo confirmado
    if pedido.estado.lower() != "confirmado":
        return jsonify({"error": f"El pedido ya fue {pedido.estado.lower()}."}), 409

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Debe enviar un JSON válido."}), 400

    fecha = data.get("fecha")
    detalles = data.get("detalles", [])

    if not fecha or not detalles:
        return jsonify({"error": "La fecha y los detalles son obligatorios."}), 400

    # 5. Validar primero todos los nuevos detalles
    detalles_validados = []
    duplicados = set()

    for item in detalles:
        person_id = item.get("person_id")
        tipo_comida = item.get("tipo_comida")

        if not person_id or not tipo_comida:
            return (
                jsonify({"error": "Cada detalle debe tener person_id y tipo_comida."}),
                400,
            )

        if tipo_comida not in {"desayuno", "almuerzo", "merienda", "cena"}:
            return jsonify({"error": f"Tipo de comida inválido: {tipo_comida}."}), 400

        # Una misma persona no puede aparecer dos veces
        # para la misma comida
        clave = (person_id, tipo_comida)

        if clave in duplicados:
            return (
                jsonify(
                    {
                        "error": f"La persona {person_id} está repetida para {tipo_comida}."
                    }
                ),
                400,
            )

        duplicados.add(clave)

        persona = Personal.obtener_personal_por_id(person_id)

        if persona is None:
            return jsonify({"error": f"No existe la persona {person_id}."}), 400

        if not persona.activo:
            return jsonify({"error": f"La persona {person_id} está inactiva."}), 400

        # Personal fijo debe ser del sector.
        # Residente tiene sector_id = None.
        if persona.sector_id is not None and persona.sector_id != sector_id:
            return (
                jsonify(
                    {
                        "error": f"La persona {person_id} no pertenece al sector del Jefe."
                    }
                ),
                400,
            )

        cupo = Cupo.obtener_por_sector_y_tipo_comida(sector_id, tipo_comida)

        if cupo is None:
            return jsonify({"error": f"No existe cupo para {tipo_comida}."}), 400

        detalles_validados.append(
            {
                "persona": persona,
                "tipo_comida": tipo_comida,
                "cupo": cupo,
            }
        )

    # 6. Verificar que al cambiar la fecha no exista otro pedido
    pedido_misma_fecha = Pedido.obtener_por_sector_y_fecha(sector_id, fecha)

    if pedido_misma_fecha is not None and pedido_misma_fecha.id != pedido.id:
        return jsonify({"error": "Ya existe un pedido para ese sector y fecha."}), 409

    # 7. Actualizar cabecera
    pedido.fecha = fecha

    # 8. Eliminar detalles anteriores
    SolicitudDetalle.eliminar_por_pedido(pedido.id)

    # 9. Recrearlos recalculando Regular / Excepción
    contadores = {
        "desayuno": 0,
        "almuerzo": 0,
        "merienda": 0,
        "cena": 0,
    }

    for item in detalles_validados:
        persona = item["persona"]
        tipo_comida = item["tipo_comida"]
        cupo = item["cupo"]

        if contadores[tipo_comida] < cupo.cantidad_comensales:
            condicion = "regular"
        else:
            condicion = "excepcion"

        detalle = SolicitudDetalle(
            pedido_id=pedido.id,
            person_id=persona.id,
            person_dni_snapshot=persona.dni,
            person_nombre_snapshot=persona.nombre,
            person_apellido_snapshot=persona.apellido,
            tipo_personal_id_snapshot=persona.tipo_personal_id,
            sector_id_snapshot=persona.sector_id,
            activo_snapshot=persona.activo,
            tipo_comida=tipo_comida,
            tipo_menu_id=persona.menu_id,
            condicion=condicion,
            estado_autorizacion="pendiente",
        )

        detalle.guardar()

        contadores[tipo_comida] += 1

    pedido.guardar()

    return (
        jsonify(
            {"mensaje": "Pedido actualizado correctamente.", "pedido_id": pedido.id}
        ),
        200,
    )
