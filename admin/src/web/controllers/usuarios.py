from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from src.web.helpers.auth import role_required, check_permission,current_user_id
from src.web.validators.usuarios import (
    validar_usuario_creacion,
    validar_usuario_edicion,
)
from src.core.usuarios import User, FiltrosUsuario
from src.core.roles import Role, NombreRol
from src.core.permisos import NombrePermiso
from src.core.sectores import Sector
from src.core.security import hashear_password
import logging

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")
logger = logging.getLogger(__name__)

@usuarios_bp.get("")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_INDEX)
def index():
    """Muestra el listado de usuarios con filtros."""

    activo_param = request.args.get("activo")
    activo = {"true": True, "false": False}.get(activo_param)

    filtros = FiltrosUsuario(
        email=request.args.get("email"),
        nombre=request.args.get("nombre"),
        apellido=request.args.get("apellido"),
        dni=request.args.get("dni"),
        activo=activo,
        rol_id=request.args.get("rol_id", type=int),
        sector_id=request.args.get("sector_id", type=int),
        ordenar_por=request.args.get("ordenar_por", "apellidoYnombre"),
        direccion=request.args.get("direccion", "asc"),
    )

    paginacion = User.buscar(filtros)

    return render_template(
        "usuarios/usuarios.html",
        usuarios=paginacion.items,
        roles=Role.obtener_todos(),
        sectores=Sector.obtener_todos_activos(),
        paginacion=paginacion,
        active_page="usuarios",
    )

@usuarios_bp.get("/nuevo")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_NEW)
def nuevo():
    """Muestra el formulario para crear un usuario."""
    rol_jefe = Role.obtener_por_nombre(NombreRol.JEFE_SERVICIO.value)
    return render_template(
        "usuarios/usuario_form.html",
        usuario=None,
        roles=Role.obtener_todos(),
        jefe_servicio_id=rol_jefe.id,
        active_page="usuarios",
    )

@usuarios_bp.post("")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_NEW)
def crear():
    """Procesa la creación de un usuario."""
    rol_jefe = Role.obtener_por_nombre(NombreRol.JEFE_SERVICIO.value)
    data = request.form.to_dict()
    data["activo"] = request.form.get("activo") == "on"
    datos, errores = validar_usuario_creacion(data)
    if errores:
        return render_template(
            "usuarios/usuario_form.html",
            usuario=None,
            datos=data,
            errores=errores,
            roles=Role.obtener_todos(),
            jefe_servicio_id=rol_jefe.id,
        )

    usuario = User(
        email=datos.email,
        nombre=datos.nombre,
        apellido=datos.apellido,
        dni=datos.dni,
        password=hashear_password(datos.password),
        activo=datos.activo,
        rol_id=datos.rol_id,
    )

    try:
        usuario.guardar()

        logger.info(
            "Usuario creado correctamente. id=%s email=%s",
            usuario.id,
            usuario.email
        )

        flash(
            "Usuario creado correctamente.",
            "success"
        )

        return redirect(
            url_for("usuarios.index")
        )

    except Exception:
        logger.exception(
            "Error al crear usuario. email=%s",
            datos.email
        )

        flash(
            "Ocurrió un error al crear el usuario.",
            "error"
        )


    return redirect(url_for("usuarios.index"))

@usuarios_bp.get("/<int:user_id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_SHOW)
def detalle(user_id):
    """Muestra el detalle de un usuario."""

    usuario = User.obtener_por_id(user_id)
    if usuario is None:
        abort(404)

    return render_template(
        "usuarios/usuario_detalle.html", usuario=usuario, active_page="usuarios"
    )

@usuarios_bp.get("/<int:user_id>/editar")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_UPDATE)
def editar(user_id):
    """Muestra el formulario de edición de un usuario."""
    rol_jefe = Role.obtener_por_nombre(NombreRol.JEFE_SERVICIO.value)
    usuario = User.obtener_por_id(user_id)
    if usuario is None:
        abort(404)
    return render_template(
        "usuarios/usuario_form.html",
        usuario=usuario,
        roles=Role.obtener_todos(),
        jefe_servicio_id=rol_jefe.id,
        active_page="usuarios",
    )

@usuarios_bp.post("/<int:user_id>/editar")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_UPDATE)
def actualizar(user_id):
    """Actualiza el usuario con lo que recibe por parametro."""
    usuario = User.obtener_por_id(user_id)
    if usuario is None:
        abort(404)

    data = request.form.to_dict()
    data["activo"] = request.form.get("activo") == "on"
    datos, errores = validar_usuario_edicion(data, usuario)
    rol_jefe = Role.obtener_por_nombre(NombreRol.JEFE_SERVICIO.value)
    if errores:
        return render_template(
            "usuarios/usuario_form.html",
            usuario=usuario,
            datos=data,
            errores=errores,
            jefe_servicio_id=rol_jefe.id,
            roles=Role.obtener_todos(),
        )

    usuario.email = datos.email
    usuario.nombre = datos.nombre
    usuario.apellido = datos.apellido
    usuario.dni = datos.dni
    usuario.activo = datos.activo
    usuario.rol_id = datos.rol_id
    
    if datos.rol_id != rol_jefe.id:
        usuario.sector_id=None

    if datos.password is not None:
        usuario.password = hashear_password(datos.password)

    try:
        usuario.guardar()

        logger.info(
            "Usuario actualizado correctamente. id=%s",
            usuario.id
        )

        flash(
            "Usuario actualizado correctamente.",
            "success"
        )

        return redirect(
            url_for("usuarios.index")
        )

    except Exception:
        logger.exception(
            "Error al actualizar usuario. id=%s",
            usuario.id
        )

        flash(
            "Ocurrió un error al actualizar el usuario.",
            "error"
        )

    return redirect(
        url_for(
            "usuarios.editar",
            user_id=usuario.id
        )
    )

@usuarios_bp.post("/<int:user_id>/eliminar")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.USER_DESTROY)
def eliminar(user_id):
    usuario = User.obtener_por_id(user_id)

    if usuario is None:
        abort(404)

    # No permitir eliminar al usuario actualmente logueado
    if usuario.id == current_user_id():
        flash(
            "No podés eliminar tu propio usuario mientras tenés la sesión iniciada.",
            "error",
        )
        return redirect(url_for("usuarios.index"))
    
    try:
        if usuario.rol.nombre == NombreRol.ADMINISTRADOR:
            if User.cantidad_administradores() <= 1:
                flash(
                    "No se puede eliminar el último usuario administrador.",
                    "error",
                )
                return redirect(url_for("usuarios.index"))
        
        if usuario.tiene_operaciones_asociadas():
            usuario.desactivar()

            logger.info(
                "Usuario desactivado por tener operaciones asociadas. id=%s",
                usuario.id
            )

            flash(
                "El usuario tiene operaciones asociadas y fue desactivado.",
                "warning"
            )
        else:
            usuario.eliminar()

            logger.info(
                "Usuario eliminado correctamente. id=%s",
                usuario.id
            )

            flash(
                "Usuario eliminado correctamente.",
                "success"
            )

    except ValueError as e:
        flash(str(e), "error")
        
    except Exception:
        logger.exception(
            "Error al eliminar/desactivar usuario. id=%s",
            usuario.id
        )

        flash(
            "Ocurrió un error al procesar el usuario.",
            "error"
        )

    return redirect(url_for("usuarios.index"))