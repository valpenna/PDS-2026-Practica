"""
Endpoints para resúmenes de pedidos, autorizaciones y entregas.
"""
from flask import Blueprint, request, jsonify, g
from src.core.roles import NombreRol
from src.web.api.helpers import token_required, api_role_required
from src.core.resumenes import (
    obtener_resumen_pedidos,
    obtener_resumen_autorizaciones,
    obtener_resumen_entregas,
)

summaries_api_bp = Blueprint("summaries_api", __name__, url_prefix="/api/summaries")


def _extraer_filtros():
    """Extrae y normaliza parámetros de query comunes."""
    return {
        "fecha_desde": request.args.get("fecha_desde"),
        "fecha_hasta": request.args.get("fecha_hasta"),
        "sector_id": request.args.get("sector_id", type=int),
        "tipo_comida": request.args.get("tipo_comida"),
        "tipo_menu_id": request.args.get("tipo_menu_id", type=int),
        "agrupamiento": request.args.get("agrupamiento", "comida").lower(),
    }


@summaries_api_bp.get("/requests")
@token_required
@api_role_required(NombreRol.ALIMENTACION, NombreRol.JEFE_SERVICIO)
def summaries_requests():
    """
    GET /api/summaries/requests
    Resumen de pedidos para Servicio de Alimentación y Jefe de Servicio.
    """
    filtros = _extraer_filtros()

    # Regla de negocio: Jefe de Servicio limitado a su sector
    if g.current_user.rol and g.current_user.rol.nombre == NombreRol.JEFE_SERVICIO.value:
        filtros["sector_id"] = g.current_user.sector_id

    try:
        data = obtener_resumen_pedidos(**filtros)
        return jsonify({"resumen": data}), 200
    except ValueError as e:
        return jsonify({"error": f"Formato de fecha inválido: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": "Error al procesar el resumen de pedidos"}), 500


@summaries_api_bp.get("/authorizations")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def summaries_authorizations():
    """
    GET /api/summaries/authorizations
    Resumen de pedidos vs autorizados.
    """
    filtros = _extraer_filtros()

    try:
        data = obtener_resumen_autorizaciones(**filtros)
        return jsonify({"resumen": data}), 200
    except ValueError as e:
        return jsonify({"error": f"Formato de fecha inválido: {str(e)}"}), 400
    except Exception:
        return jsonify({"error": "Error al procesar el resumen de autorizaciones"}), 500


@summaries_api_bp.get("/deliveries")
@token_required
@api_role_required(NombreRol.ALIMENTACION)
def summaries_deliveries():
    """
    GET /api/summaries/deliveries
    Resumen de autorizados vs entregados.
    """
    filtros = _extraer_filtros()

    try:
        data = obtener_resumen_entregas(**filtros)
        return jsonify({"resumen": data}), 200
    except ValueError as e:
        return jsonify({"error": f"Formato de fecha inválido: {str(e)}"}), 400
    except Exception:
        return jsonify({"error": "Error al procesar el resumen de entregas"}), 500