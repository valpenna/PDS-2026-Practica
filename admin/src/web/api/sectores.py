from functools import wraps
from types import SimpleNamespace
from datetime import datetime
from flask import Blueprint, abort, g, jsonify, request, session
from werkzeug.exceptions import HTTPException
from src.web.api.helpers import token_required
from src.core.roles import NombreRol
from src.core.sectores import Sector
from src.core.usuarios import User

sectores_api_bp = Blueprint("api_sectores", __name__, url_prefix="/api/sectors")


@sectores_api_bp.errorhandler(HTTPException)
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


@sectores_api_bp.get("/")
@token_required
def listar_sectores():
    """
    Proposito: Lista sectores activos o todos, según el filtro solicitado.
    Entrada: Query parameter activo (true/false) para filtrar sectores activos o inactivos
    Salida: JSON con listado de sectores
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar sectores."}),
            403,
        )

    estado = request.args.get("estado", "activo")
    if estado not in {"activo", "todos"}:
        return (
            jsonify({"error": "El parámetro 'estado' debe ser 'activo' o 'todos'."}),
            403,
        )

    sectores = (
        Sector.obtener_todos_activos() if estado == "activo" else Sector.obtener_todos()
    )
    return (
        jsonify(
            [
                {
                    "id": sector.id,
                    "nombre": sector.nombre,
                    "descripcion": sector.descripcion,
                    "estado": "activo" if sector.activo else "inactivo",
                    "jefe_servicio": [
                        {
                            "email": jefe.email,
                            "nombre": jefe.nombre,
                            "apellido": jefe.apellido,
                            "dni": jefe.dni,
                            "activo": jefe.activo,
                            "fecha_creacion": jefe.fecha_creacion,
                            "fecha_modificacion": jefe.fecha_modificacion,
                        }
                        for jefe in User.obtener_por_sector(sector.id)
                    ],
                }
                for sector in sectores
            ]
        ),
        200,
    )


@sectores_api_bp.get("/<int:sector_id>")
@token_required
def obtener_sector(sector_id):
    """
    Proposito: Obtiene el sector correspondiente a un ID
    Entrada: ID de sector
    Salida: JSON con el sector y sus jefes de servicio
    """
    usuario = g.current_user
    roles_permitidos = {
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
    }
    if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
        return (
            jsonify({"error": "El rol del usuario no puede consultar sectores."}),
            403,
        )

    sector = Sector.obtener_por_id(sector_id)
    if not sector:
        return (jsonify({"error": "No existe el sector solicitado"}), 404)
    return (
        jsonify(
            {
                "id": sector.id,
                "nombre": sector.nombre,
                "descripcion": sector.descripcion,
                "activo": sector.activo,
                "fecha_creacion": sector.fecha_creacion,
                "fecha_modificacion": sector.fecha_modificacion,
                "jefes_servicio": [
                    {
                        "email": jefe.email,
                        "nombre": jefe.nombre,
                        "apellido": jefe.apellido,
                        "dni": jefe.dni,
                        "activo": jefe.activo,
                        "fecha_creacion": jefe.fecha_creacion,
                        "fecha_modificacion": jefe.fecha_modificacion,
                    }
                    for jefe in User.obtener_por_sector(sector.id)
                ],
            }
        ),
        200,
    )
