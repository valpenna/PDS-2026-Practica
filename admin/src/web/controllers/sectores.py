from src.core.permisos import NombrePermiso
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from src.core.roles import NombreRol
from src.web.helpers.auth import login_required, role_required, check_permission
from src.web.validators.sectores import validar_sector_creacion, validar_sector_edicion
from src.core.sectores import FiltrosSector, Sector
from src.core.usuarios import User
from src.core.personal import Personal
from src.core.pedidos import Pedido
from src.core.configuracion import Configuracion
import logging

logger = logging.getLogger(__name__)
sectores_bp = Blueprint("sectores", __name__, url_prefix="/sectores")


@sectores_bp.get("")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_INDEX)
def index():
    """Muestra el listado de sectores."""

    filtros = FiltrosSector(
        nombre=request.args.get("nombre"),
        activo={"true": True, "false": False}.get(request.args.get("activo")),
        direccion=request.args.get("direccion", "asc"),
        ordenar_por=request.args.get("ordenar_por", "nombre"),
        con_jefes={"true": True, "false": False}.get(request.args.get("con_jefes")),
    )

    paginacion = Sector.buscar(filtros)
    return render_template(
        "sectores/sectores.html",
        sectores=paginacion.items,
        paginacion=paginacion,
        active_page="sectores",
    )


@sectores_bp.get("/nuevo")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_NEW)
def nuevo():
    """Muestra el formulario para crear un sector."""
    usuarios = User.obtener_jefes_de_servicio()
    logger.info("Renderizando formulario")
    return render_template(
        "sectores/sector_form.html",
        modo="crear",
        sector=None,
        active_page="sectores",
        jefes_servicio=usuarios,
        jefes_seleccionados=[],
    )


@sectores_bp.post("/nuevo")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_NEW)
def crear():
    """Crea un nuevo sector."""
    data = request.form.to_dict()
    data["jefes_servicio"] = request.form.getlist("jefes_servicio")
    data["activo"] = "on" in request.form.getlist("activo")
    logger.info("Validando creacion de sector")
    datos, errores = validar_sector_creacion(data)

    if errores:
        logger.error("Errores en la creación de sector.")
        flash("Errores listados en el formulario.", "error")
        return render_template(
            "sectores/sector_form.html",
            modo="crear",
            sector=None,
            datos=data,
            errores=errores,
            jefes_servicio=User.obtener_jefes_de_servicio(),
            jefes_seleccionados=[str(jefe_id) for jefe_id in data["jefes_servicio"]],
        )
    sector = Sector(
        nombre=datos.nombre, descripcion=datos.descripcion, activo=datos.activo
    )
    sector.guardar()
    for jefe_id in datos.jefes_servicio:
        user = User.obtener_por_id(int(jefe_id))
        user.sector_id = sector.id
        user.guardar()
    con_jefes = ""
    if datos.jefes_servicio:
        con_jefes = "Usuarios actualizados."
    logger.info(f"Sector '{datos.nombre}' creado correctamente. {con_jefes}")
    flash(f"Sector '{datos.nombre}' creado correctamente. {con_jefes}", "success")
    return redirect(url_for("sectores.index"))


@sectores_bp.get("/eliminar/<int:id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_DESTROY)
def eliminar(id):
    """Elimina un sector por su ID."""
    sector = Sector.obtener_por_id(id)
    if sector:
        usuarios = User.obtener_por_sector(id)
        personal = Personal.obtener_por_sector(id)
        pedidos = Pedido.obtener_por_sector(id)

        asociaciones = [
            nombre
            for nombre, registros in (
                ("usuarios", usuarios),
                ("personal", personal),
                ("pedidos", pedidos),
            )
            if registros
        ]
        desactivar = bool(asociaciones)

        if desactivar:
            detalle = ", ".join(asociaciones[:-1])
            if detalle:
                detalle = f"{detalle} y {asociaciones[-1]}"
            else:
                detalle = asociaciones[0]
            mensaje = (
                "No se pudo eliminar el sector porque hay registros asociados "
                f"({detalle}). El sector fue desactivado."
            )
            sector.activo = False
            sector.guardar()
            logger.warning(mensaje)
            flash(mensaje, "error")
        else:
            Sector.eliminar_sector(id)
            logger.info("Sector eliminado correctamente.")
            flash("Sector eliminado correctamente.", "success")
    else:
        logger.error("No se encontró el sector a eliminar.")
        flash("No se encontró el sector a eliminar.", "error")
    return redirect(url_for("sectores.index"))


@sectores_bp.get("/ver/<int:id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_SHOW)
def ver(id):
    """Muestra los detalles de un sector por su ID."""
    sector = Sector.obtener_por_id(id)
    jefes_servicio = User.obtener_por_sector(id)
    if not sector:
        logger.error("El sector no fue encontrado.")
        flash("El sector no fue encontrado.", "error")
        return redirect(url_for("sectores.index"))
    logger.info("Mostrando sector.")
    return render_template(
        "sectores/sector_detalle.html",
        sector=sector,
        jefes_servicio=jefes_servicio,
        active_page="sectores",
    )


@sectores_bp.get("/editar/<int:id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_UPDATE)
def editar(id):
    """Muestra el formulario para editar un sector."""
    sector = Sector.obtener_por_id(id)
    if not sector:
        logger.error("No se encontró el sector a editar.")
        flash("No se encontró el sector a editar.", "error")
        return redirect(url_for("sectores.index"))
    logger.info("Mostrando sector.")
    return render_template(
        "sectores/sector_form.html",
        modo="editar",
        sector=sector,
        active_page="sectores",
        jefes_servicio=User.obtener_jefes_de_servicio(),
        jefes_seleccionados=[str(jefe.id) for jefe in User.obtener_por_sector(id)],
    )


@sectores_bp.post("/editar/<int:id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.SECTOR_UPDATE)
def actualizar(id):
    """Actualiza un sector existente."""
    sector = Sector.obtener_por_id(id)
    if not sector:
        logger.error("No se encontró el sector a actualizar.")
        flash("No se encontró el sector a actualizar.", "error")
        return redirect(url_for("sectores.index"))

    data = request.form.to_dict()
    data["jefes_servicio"] = request.form.getlist("jefes_servicio")

    data["activo"] = "on" in request.form.getlist("activo")
    datos, errores = validar_sector_edicion(data, id)
    if errores:
        logger.error("Errores en la actualización del sector.")
        flash("Errores listados en el formulario.", "error")
        return render_template(
            "sectores/sector_form.html",
            modo="editar",
            sector=sector,
            datos=data,
            errores=errores,
            active_page="sectores",
            jefes_servicio=User.obtener_jefes_de_servicio(),
            jefes_seleccionados=[str(jefe_id) for jefe_id in data["jefes_servicio"]],
        )

    sector.nombre = datos.nombre
    sector.descripcion = datos.descripcion
    sector.activo = datos.activo
    try:
        sector.guardar()
        # Elimina el sector de los usuarios no pertenecientes a la lista de jefes de servicio
        for user in User.obtener_por_sector(id):
            if str(user.id) not in datos.jefes_servicio:
                user.sector_id = None
                user.guardar()
        # Agrega el sector a los usuarios que son jefes de servicio y no lo tenían asignado
        for jefe_id in datos.jefes_servicio:
            user = User.obtener_por_id(int(jefe_id))
            user.sector_id = sector.id
            user.guardar()
        con_jefes = ""
        if datos.jefes_servicio:
            con_jefes = "Usuarios actualizados."
        logger.info(f"Sector '{datos.nombre}' actualizados correctamente. {con_jefes}")
        flash(
            f"Sector '{datos.nombre}' actualizados correctamente. {con_jefes}",
            "success",
        )
    except Exception as e:
        flash(f"No se pudo actualizar el sector: {str(e)}", "error")
        return redirect(url_for("sectores.editar", id=id))
    return redirect(url_for("sectores.ver", id=id))
