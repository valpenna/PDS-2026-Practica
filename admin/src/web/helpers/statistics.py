from src.core.roles import Role
from src.core.usuarios import User
from src.core.sectores import Sector
from src.core.tipos_menu import TipoMenu
from src.core.personal import Personal
from src.core.tipos_personal import TipoPersonal


def obtener_estadisticas_usuarios():
    usuarios = User.obtener_todos()
    roles = Role.obtener_todos()
    stats = {
        "total": len(usuarios),
        "activos": 0,
        "inactivos": 0,
        "con_sector_asignado": len(User.obtener_jefes_de_servicio()),
        **{rol.nombre: 0 for rol in roles},
    }
    nombres_roles = {rol.id: rol.nombre for rol in roles}

    for usuario in usuarios:
        stats[nombres_roles[usuario.rol_id]] += 1
        if usuario.activo:
            stats["activos"] += 1
        else:
            stats["inactivos"] += 1

    return stats


def obtener_estadisticas_sectores():
    sectores = Sector.obtener_todos()
    totales = len(sectores)
    activos = len(Sector.obtener_todos_activos())
    sectores_con_jefes = Sector.obtener_todos_con_jefes()
    con_jefes = 0
    for sector in sectores_con_jefes:
        jefe = sector.jefes_servicio
        if jefe:
            con_jefes += 1
    inactivos = totales - activos

    stats = {
        "total": totales,
        "activos": activos,
        "inactivos": inactivos,
        "con_jefes_asignado": con_jefes,
    }
    return stats


def obtener_estadisticas_personal():
    menus = TipoMenu.obtener_todos()
    tipo_personal = TipoPersonal.obtener_todos()
    personal = Personal.obtener_todos()
    stats = {
        "total": len(personal),
        "activos": 0,
        "inactivos": 0,
        **{tipo.nombre: 0 for tipo in tipo_personal},
        **{menu.nombre: 0 for menu in menus},
    }
    nombres_menus = {menu.id: menu.nombre for menu in menus}
    nombres_tipo_personal = {tipo.id: tipo.nombre for tipo in tipo_personal}

    for persona in personal:
        if persona.activo:
            stats["activos"] += 1
        else:
            stats["inactivos"] += 1
        stats[nombres_menus[persona.menu_id]] += 1
        stats[nombres_tipo_personal[persona.tipo_personal_id]] += 1
    return stats
