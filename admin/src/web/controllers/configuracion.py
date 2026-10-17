from flask import Blueprint, flash, redirect, render_template, request, url_for
from src.core.configuracion import Configuracion
from src.core.roles import NombreRol
from src.web.helpers.auth import check_permission, login_required, role_required
from src.web.validators.configuracion import validar_configuracion


configuracion_bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")


@configuracion_bp.before_request
@login_required
@role_required(NombreRol.ADMINISTRADOR)
@check_permission("configuration_show")
def require_admin_for_all_configuracion():
    pass


@configuracion_bp.get("/")
def index():
    """Muestra el formulario de configuración del sistema."""
    config = Configuracion.obtener()
    return render_template("configuracion/index.html", config=config, active_page="configuracion")


@configuracion_bp.post("/actualizar")
def actualizar():
    """Guarda los cambios de la configuración."""
    config = Configuracion.obtener()

    elementos_str = request.form.get("elementos_por_pagina", "").strip()
    sitio_en_mantenimiento = request.form.get("sitio_en_mantenimiento") == "on"
    mensaje_mantenimiento = request.form.get("mensaje_mantenimiento", "").strip()

    # Delegación de validación al módulo específico
    errores = validar_configuracion(elementos_str, sitio_en_mantenimiento, mensaje_mantenimiento)

    if errores:
        for err in errores:
            flash(err, "danger")
        return render_template("configuracion/index.html", config=config, active_page="configuracion")

    try:
        config.actualizar(
            elementos_por_pagina=int(elementos_str),
            sitio_en_mantenimiento=sitio_en_mantenimiento,
            mensaje_mantenimiento=mensaje_mantenimiento if sitio_en_mantenimiento else None
        )
        flash("Configuración actualizada con éxito.", "success")
    except Exception:
        flash("Error inesperado al guardar la configuración.", "danger")

    return redirect(url_for("configuracion.index"))