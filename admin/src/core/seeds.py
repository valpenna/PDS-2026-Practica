"""Módulo para sembrar la base de datos con los roles, sectores y usuarios iniciales."""

import os
from src.core.db import db
from src.core.roles import Role, RolPermiso
from src.core.permisos import Permiso
from src.core.usuarios import User
from src.core.security import hashear_password
from src.core.tipos_personal import TipoPersonal
from src.core.tipos_menu import TipoMenu


def seed_roles_y_permisos():
    """Crea los 4 roles del sistema y asocia los permisos de usuario al Administrador."""
    nombres_roles = [
        "Administrador",
        "Jefe de Servicio",
        "Servicio de Alimentación",
        "Sector Comedor",
    ]
    roles = {}
    for nombre in nombres_roles:
        rol = Role.obtener_por_nombre(nombre)
        if not rol:
            rol = Role(nombre=nombre)
            db.session.add(rol)
        roles[nombre] = rol

    db.session.flush()

    permisos_base = [
        "sector_index",
        "sector_new",
        "sector_update",
        "sector_destroy",
        "sector_show",
        "user_index",
        "user_new",
        "user_update",
        "user_destroy",
        "user_show",
        "configuration_show",
        "personal_index",
        "personal_new",
        "personal_update",
        "personal_destroy",
        "personal_show",
        "personal_import",
    ]
    permisos = []
    for nombre in permisos_base:
        permiso = Permiso.obtener_por_nombre(nombre)
        if not permiso:
            permiso = Permiso(nombre=nombre)
            db.session.add(permiso)
        permisos.append(permiso)

    db.session.flush()

    # Asignar los permisos al rol Administrador
    admin_rol = roles["Administrador"]
    for permiso in permisos:
        relacion = RolPermiso.obtener_rol_permiso(admin_rol.id, permiso.id)
        if not relacion:
            db.session.add(RolPermiso(rol_id=admin_rol.id, permiso_id=permiso.id))

    db.session.commit()
    return roles


def seed_usuarios(roles):
    """Crea únicamente el usuario administrador inicial a partir de variables de entorno."""
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        raise RuntimeError("No está configurada la variable de entorno ADMIN_PASSWORD.")

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@hospital.com")
    admin_hash = hashear_password(admin_password)

    existente = User.obtener_por_email(admin_email)
    if not existente:
        admin_user = User(
            email=admin_email,
            nombre="Esteban",
            apellido="Admin",
            dni="10000001",
            password=admin_hash,
            activo=True,
            rol_id=roles["Administrador"].id,
            sector_id=None,
        )
        db.session.add(admin_user)
        db.session.commit()

def seed_tipos_personal():
    """Inserta los tipos de personal iniciales que todavía no existen."""
    tipo_personal = [
        TipoPersonal(nombre="Personal Fijo"),
        TipoPersonal(nombre="Residente"),
    ]

    for tipo in tipo_personal:
        existente = TipoPersonal.obtener_por_nombre(tipo.nombre)
        if not existente:
            db.session.add(tipo)
    db.session.commit()

def seed_tipos_menu():
    """Inserta los tipos de menú iniciales que todavía no existen."""
    tipo_menu = [
        TipoMenu(nombre="General"),
        TipoMenu(nombre="Celíaco"),
        TipoMenu(nombre="Vegetariano"),
    ]

    for tipo in tipo_menu:
        existente = TipoMenu.obtener_por_nombre(tipo.nombre)
        if not existente:
            db.session.add(tipo)
    db.session.commit()


def run():
    """Punto de entrada para ejecutar el sembrado."""
    roles = seed_roles_y_permisos()
    seed_usuarios(roles)
    seed_tipos_personal()
    seed_tipos_menu()
    print("Seed completada exitosamente.")
