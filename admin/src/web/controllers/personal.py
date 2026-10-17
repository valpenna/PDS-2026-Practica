from src.core.permisos import NombrePermiso
from src.core.roles import NombreRol
from flask import Blueprint, Response, render_template, request, redirect, url_for, flash, abort
from src.web.helpers.auth import check_permission, role_required
from src.core.personal import FiltrosPersonal, Personal
from src.core.sectores import Sector
from src.core.tipos_personal import TipoPersonal
from src.web.validators.personal import validar_personal_creacion, validar_personal_edicion
from src.core.tipos_menu import TipoMenu
from src.core.configuracion import Configuracion
from src.web.services.importacion_personal import procesar_csv_personal

personal_bp = Blueprint("personal", __name__, url_prefix="/personal")


@personal_bp.get("")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_INDEX)
def index():
    """Muestra el listado de personal."""
    pagina = request.args.get("pagina", 1, type=int)
    if pagina < 1:
        pagina = 1

    config = Configuracion.obtener()
    por_pagina = min(max(config.elementos_por_pagina, 1), 25)

    filtros = FiltrosPersonal(
        nombre=request.args.get("nombre"),
        apellido=request.args.get("apellido"),
        dni=request.args.get("dni"),
        sector_id=request.args.get("sector_id", type=int),
        activo={"true": True, "false": False}.get(request.args.get("activo")),
        tipo_personal_id=request.args.get("tipo_personal_id", type=int),
        pagina=pagina,
        por_pagina=por_pagina,
        direccion=request.args.get("direccion", "asc"),
        ordenar_por=request.args.get("ordenar_por", "nombre"),
    )
    personal, total = Personal.buscar(filtros)
    total_paginas = (total + por_pagina - 1) // por_pagina if por_pagina and total else 0

    return render_template(
        "personal/personal.html",
        personal=personal,
        tipos_personal=TipoPersonal.obtener_todos(),
        sectores=Sector.obtener_todos_activos(),
        pagina=pagina,
        total_paginas=total_paginas,
        active_page="personal",
    )


@personal_bp.get("/nuevo")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_NEW)
def nuevo_personal():
    """Muestra el formulario para crear un nuevo personal."""
    return render_template(
        "personal/personal_form.html",
        modo="crear",
        personal=None,
        sectores=Sector.obtener_todos_activos(),
        tipos_personal=TipoPersonal.obtener_todos(),
        tipos_menu=TipoMenu.obtener_todos(),
        active_page="personal",
        errores={},
    )


@personal_bp.post("/nuevo")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_NEW)
def crear_personal():
    """Procesa la creación de un nuevo personal."""
    data = request.form.to_dict()
    data["activo"] = True
    datos, errores = validar_personal_creacion(data)

    if errores:
        return render_template(
            "personal/personal_form.html",
            modo="crear",
            personal=None,
            sectores=Sector.obtener_todos_activos(),
            tipos_personal=TipoPersonal.obtener_todos(),
            tipos_menu=TipoMenu.obtener_todos(),
            active_page="personal",
            errores=errores,
            datos=data,
        )

    Personal.crear_personal(datos.model_dump())
    flash("Personal creado correctamente.", "success")
    return redirect(url_for("personal.index"))


@personal_bp.get("/ver/<int:personal_id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_SHOW)
def ver_personal(personal_id):
    """Muestra el detalle de un registro de personal."""
    personal = Personal.obtener_personal_por_id(personal_id)
    if not personal:
        abort(404, description="Personal no encontrado.")

    return render_template(
        "personal/personal_detalle.html",
        personal=personal,
        tipo_personal=TipoPersonal.obtener_por_id(personal.tipo_personal_id),
        sector=Sector.obtener_por_id(personal.sector_id) if personal.sector_id else None,
        tipo_menu=TipoMenu.obtener_por_id(personal.menu_id),
        active_page="personal",
    )


@personal_bp.get("/editar/<int:personal_id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_UPDATE)
def formulario_editar_personal(personal_id):
    """Muestra el formulario para editar un registro de personal."""
    personal = Personal.obtener_personal_por_id(personal_id)
    if not personal:
        abort(404, description="Personal no encontrado.")

    sectores = Sector.obtener_todos_activos()
    sector_actual = Sector.obtener_por_id(personal.sector_id) if personal.sector_id else None
    if sector_actual and not sector_actual.activo:
        sectores.append(sector_actual)

    return render_template(
        "personal/personal_form.html",
        modo="editar",
        personal=personal,
        sectores=sectores,
        tipos_personal=TipoPersonal.obtener_todos(),
        tipos_menu=TipoMenu.obtener_todos(),
        active_page="personal",
        errores={},
    )


@personal_bp.post("/editar/<int:personal_id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_UPDATE)
def editar_personal(personal_id):
    """Procesa la actualización de un personal existente."""
    personal = Personal.obtener_personal_por_id(personal_id)
    if not personal:
        abort(404, description="Personal no encontrado.")

    data = request.form.to_dict()
    data["activo"] = "on" in request.form.getlist("activo")

    datos, errores = validar_personal_edicion(data, personal)

    if errores:
        sectores = Sector.obtener_todos_activos()
        sector_actual = Sector.obtener_por_id(personal.sector_id) if personal.sector_id else None
        if sector_actual and not sector_actual.activo:
            sectores.append(sector_actual)
        return render_template(
            "personal/personal_form.html",
            modo="editar",
            personal=personal,
            sectores=sectores,
            tipos_personal=TipoPersonal.obtener_todos(),
            tipos_menu=TipoMenu.obtener_todos(),
            active_page="personal",
            errores=errores,
            datos=data,
        )

    Personal.actualizar_personal(personal_id, datos.model_dump())
    flash("Personal actualizado correctamente.", "success")
    return redirect(url_for("personal.ver_personal", personal_id=personal_id))


@personal_bp.post("/eliminar/<int:personal_id>")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_DESTROY)
def eliminar_personal(personal_id):
    """Procesa la eliminación de un personal existente."""
    personal = Personal.obtener_personal_por_id(personal_id)

    if not personal:
        flash("Personal no encontrado.", "error")
        return redirect(url_for("personal.index"))

    if not personal.activo:
        flash("Este personal ya estaba eliminado.", "error")
        return redirect(url_for("personal.index"))
    if Personal.tiene_historial(personal_id):
        Personal.marcar_como_inactivo(personal_id)
        flash("Personal marcado como inactivo para conservar su historial.", "success")
    else:
        Personal.eliminar_personal(personal_id)
        flash("Personal eliminado correctamente.", "success")

    return redirect(url_for("personal.index"))


@personal_bp.get("/importar")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_IMPORT)
def importar_personal():
    """Muestra el formulario para importar personal desde un archivo CSV."""
    return render_template(
        "personal/personal_importar.html",
        active_page="personal",
        tipos_personal=TipoPersonal.obtener_todos(),
        tipos_menu=TipoMenu.obtener_todos(),
    )

@personal_bp.get("/descargar-plantilla")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_IMPORT)
def descargar_plantilla_csv():
    """Descarga una plantilla de ejemplo para la importación de personal."""
    # Encabezado + un par de filas de ejemplo (Personal Fijo y Residente)
    contenido_csv = (
        "dni,nombre,apellido,tipo_personal,sector,menu\n"
        "12345678,Juan,Perez,Personal Fijo,Quirófano,General\n"
        "87654321,Maria,Gomez,Residente,,Vegetariano\n"
    )
    return Response(
        contenido_csv,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_personal.csv"},
    )

@personal_bp.post("/importar")
@role_required(NombreRol.ADMINISTRADOR)
@check_permission(NombrePermiso.PERSONAL_IMPORT)
def procesar_importacion_personal():
    """Procesa la importación de personal desde un archivo CSV."""
    archivo = request.files.get("archivo_csv")

    if not archivo or archivo.filename == "":
        flash("No se ha seleccionado ningún archivo.", "error")
        return redirect(url_for("personal.importar_personal"))

    if not archivo.filename.lower().endswith(".csv"):
        flash("El archivo debe tener extensión .csv.", "error")
        return redirect(url_for("personal.importar_personal"))

    try:
        contenido = archivo.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        flash(
            "El archivo no está codificado en UTF-8. Guardalo como CSV UTF-8 e intentá nuevamente.",
            "error",
        )
        return redirect(url_for("personal.importar_personal"))

    resultado = procesar_csv_personal(contenido)

    return render_template(
        "personal/personal_importar.html",
        active_page="personal",
        resultado=resultado,
    )
        