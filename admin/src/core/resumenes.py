from datetime import datetime, date
from sqlalchemy import select, func, and_
from src.core.db import db
from src.core.pedidos import Pedido
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.entregas import EntregaDetalle
from src.core.sectores import Sector
from src.core.tipos_menu import TipoMenu


def _aplicar_filtros_base(consulta, fecha_desde=None, fecha_hasta=None, sector_id=None, tipo_comida=None, tipo_menu_id=None):
    """Aplica filtros comunes sobre Pedido y SolicitudDetalle."""
    if fecha_desde:
        if isinstance(fecha_desde, str):
            fecha_desde = date.fromisoformat(fecha_desde)
        consulta = consulta.where(Pedido.fecha >= fecha_desde)
    if fecha_hasta:
        if isinstance(fecha_hasta, str):
            fecha_hasta = date.fromisoformat(fecha_hasta)
        consulta = consulta.where(Pedido.fecha <= fecha_hasta)
    if sector_id:
        consulta = consulta.where(Pedido.sector_id == sector_id)
    if tipo_comida:
        consulta = consulta.where(SolicitudDetalle.tipo_comida == tipo_comida.lower())
    if tipo_menu_id:
        consulta = consulta.where(SolicitudDetalle.tipo_menu_id == tipo_menu_id)
    return consulta


def obtener_resumen_pedidos(fecha_desde=None, fecha_hasta=None, sector_id=None, tipo_comida=None, tipo_menu_id=None, agrupamiento="comida"):
    """
    Retorna el total de viandas solicitadas según filtros y criterio de agrupación.
    """
    # Excluimos pedidos rechazados
    condiciones = [SolicitudDetalle.pedido_id == Pedido.id, Pedido.estado != 'rechazado']
    
    columnas_agrupamiento = []
    campos_select = []
    
    if agrupamiento == "sector":
        campos_select = [Sector.id.label("sector_id"), Sector.nombre.label("sector_nombre")]
        columnas_agrupamiento = [Sector.id, Sector.nombre]
    elif agrupamiento in ("dia", "fecha"):
        campos_select = [Pedido.fecha.label("fecha")]
        columnas_agrupamiento = [Pedido.fecha]
    elif agrupamiento == "mes":
        campos_select = [func.to_char(Pedido.fecha, 'YYYY-MM').label("periodo")]
        columnas_agrupamiento = [func.to_char(Pedido.fecha, 'YYYY-MM')]
    elif agrupamiento == "menu":
        campos_select = [TipoMenu.id.label("tipo_menu_id"), TipoMenu.nombre.label("tipo_menu_nombre")]
        columnas_agrupamiento = [TipoMenu.id, TipoMenu.nombre]
    else:  # 'comida' por defecto
        campos_select = [SolicitudDetalle.tipo_comida.label("tipo_comida")]
        columnas_agrupamiento = [SolicitudDetalle.tipo_comida]

    consulta = (
        select(
            *campos_select,
            func.count(SolicitudDetalle.id).label("total_pedidos")
        )
        .join(Pedido, Pedido.id == SolicitudDetalle.pedido_id)
        .join(Sector, Sector.id == Pedido.sector_id)
        .join(TipoMenu, TipoMenu.id == SolicitudDetalle.tipo_menu_id)
        .where(and_(*condiciones))
    )

    consulta = _aplicar_filtros_base(consulta, fecha_desde, fecha_hasta, sector_id, tipo_comida, tipo_menu_id)
    consulta = consulta.group_by(*columnas_agrupamiento).order_by(*columnas_agrupamiento)

    resultados = db.session.execute(consulta).all()

    salida = []
    for fila in resultados:
        item = dict(fila._mapping)
        if "fecha" in item and isinstance(item["fecha"], (date, datetime)):
            item["fecha"] = item["fecha"].isoformat()
        salida.append(item)

    return salida


def obtener_resumen_autorizaciones(fecha_desde=None, fecha_hasta=None, sector_id=None, tipo_comida=None, tipo_menu_id=None, agrupamiento="comida"):
    """
    Retorna comparativa de pedidos vs autorizados con su diferencia.
    """
    campos_select = []
    columnas_agrupamiento = []

    if agrupamiento == "sector":
        campos_select = [Sector.id.label("sector_id"), Sector.nombre.label("sector_nombre")]
        columnas_agrupamiento = [Sector.id, Sector.nombre]
    elif agrupamiento in ("dia", "fecha"):
        campos_select = [Pedido.fecha.label("fecha")]
        columnas_agrupamiento = [Pedido.fecha]
    elif agrupamiento == "menu":
        campos_select = [TipoMenu.id.label("tipo_menu_id"), TipoMenu.nombre.label("tipo_menu_nombre")]
        columnas_agrupamiento = [TipoMenu.id, TipoMenu.nombre]
    else:
        campos_select = [SolicitudDetalle.tipo_comida.label("tipo_comida")]
        columnas_agrupamiento = [SolicitudDetalle.tipo_comida]

    # Total pedidos vs total autorizados
    consulta = (
        select(
            *campos_select,
            func.count(SolicitudDetalle.id).label("total_pedidos"),
            func.count(SolicitudDetalle.id).filter(SolicitudDetalle.estado_autorizacion == 'autorizado').label("total_autorizados")
        )
        .join(Pedido, Pedido.id == SolicitudDetalle.pedido_id)
        .join(Sector, Sector.id == Pedido.sector_id)
        .join(TipoMenu, TipoMenu.id == SolicitudDetalle.tipo_menu_id)
        .where(Pedido.estado != 'rechazado')
    )

    consulta = _aplicar_filtros_base(consulta, fecha_desde, fecha_hasta, sector_id, tipo_comida, tipo_menu_id)
    consulta = consulta.group_by(*columnas_agrupamiento).order_by(*columnas_agrupamiento)

    resultados = db.session.execute(consulta).all()

    salida = []
    for fila in resultados:
        item = dict(fila._mapping)
        pedidos = item.get("total_pedidos", 0)
        autorizados = item.get("total_autorizados", 0)
        item["diferencia"] = pedidos - autorizados
        if "fecha" in item and isinstance(item["fecha"], (date, datetime)):
            item["fecha"] = item["fecha"].isoformat()
        salida.append(item)

    return salida


def obtener_resumen_entregas(fecha_desde=None, fecha_hasta=None, sector_id=None, tipo_comida=None, tipo_menu_id=None, agrupamiento="comida"):
    """
    Retorna comparativa de autorizados vs entregados con su diferencia.
    """
    campos_select = []
    columnas_agrupamiento = []

    if agrupamiento == "sector":
        campos_select = [Sector.id.label("sector_id"), Sector.nombre.label("sector_nombre")]
        columnas_agrupamiento = [Sector.id, Sector.nombre]
    elif agrupamiento in ("dia", "fecha"):
        campos_select = [Pedido.fecha.label("fecha")]
        columnas_agrupamiento = [Pedido.fecha]
    elif agrupamiento == "menu":
        campos_select = [TipoMenu.id.label("tipo_menu_id"), TipoMenu.nombre.label("tipo_menu_nombre")]
        columnas_agrupamiento = [TipoMenu.id, TipoMenu.nombre]
    else:
        campos_select = [SolicitudDetalle.tipo_comida.label("tipo_comida")]
        columnas_agrupamiento = [SolicitudDetalle.tipo_comida]

    # Contamos solo autorizados, y mediante un LEFT JOIN contamos si hay entrega_detalle
    consulta = (
        select(
            *campos_select,
            func.count(SolicitudDetalle.id).label("total_autorizados"),
            func.count(EntregaDetalle.id).label("total_entregados")
        )
        .join(Pedido, Pedido.id == SolicitudDetalle.pedido_id)
        .join(Sector, Sector.id == Pedido.sector_id)
        .join(TipoMenu, TipoMenu.id == SolicitudDetalle.tipo_menu_id)
        .outerjoin(EntregaDetalle, EntregaDetalle.solicitud_detalle_id == SolicitudDetalle.id)
        .where(SolicitudDetalle.estado_autorizacion == 'autorizado')
    )

    consulta = _aplicar_filtros_base(consulta, fecha_desde, fecha_hasta, sector_id, tipo_comida, tipo_menu_id)
    consulta = consulta.group_by(*columnas_agrupamiento).order_by(*columnas_agrupamiento)

    resultados = db.session.execute(consulta).all()

    salida = []
    for fila in resultados:
        item = dict(fila._mapping)
        autorizados = item.get("total_autorizados", 0)
        entregados = item.get("total_entregados", 0)
        item["diferencia"] = autorizados - entregados
        if "fecha" in item and isinstance(item["fecha"], (date, datetime)):
            item["fecha"] = item["fecha"].isoformat()
        salida.append(item)

    return salida