"""
Módulo de Seed de prueba integral para desarrollo y testing de APIs (Resúmenes, Entregas y Pedidos).
"""
import os
from datetime import date, datetime, timedelta, timezone
from src.core.db import db
from src.core.roles import Role, RolPermiso, NombreRol
from src.core.permisos import Permiso
from src.core.usuarios import User
from src.core.sectores import Sector
from src.core.tipos_personal import TipoPersonal
from src.core.tipos_menu import TipoMenu
from src.core.personal import Personal
from src.core.pedidos import Pedido
from src.core.solicitudes_detalle import SolicitudDetalle
from src.core.entregas import Entrega, EntregaDetalle
from src.core.security import hashear_password
from sqlalchemy import select


def run():
    """Ejecuta el sembrado completo con datos de prueba."""
    print("Iniciando Seed de Testing...")

    # 1. ROLES Y PERMISOS BASE
    nombres_roles = [
        NombreRol.ADMINISTRADOR.value,
        NombreRol.JEFE_SERVICIO.value,
        NombreRol.ALIMENTACION.value,
        NombreRol.COMEDOR.value,
    ]
    roles = {}
    for nombre in nombres_roles:
        rol = Role.obtener_por_nombre(nombre)
        if not rol:
            rol = Role(nombre=nombre)
            db.session.add(rol)
        roles[nombre] = rol

    db.session.flush()

    # 2. TIPOS DE PERSONAL
    tipos_personal = {}
    for nombre in ["Personal Fijo", "Residente"]:
        t = TipoPersonal.obtener_por_nombre(nombre)
        if not t:
            t = TipoPersonal(nombre=nombre)
            db.session.add(t)
        tipos_personal[nombre] = t

    # 3. TIPOS DE MENÚ
    tipos_menu = {}
    for nombre in ["General", "Celíaco", "Vegetariano"]:
        m = TipoMenu.obtener_por_nombre(nombre)
        if not m:
            m = TipoMenu(nombre=nombre)
            db.session.add(m)
        tipos_menu[nombre] = m

    # 4. SECTORES DE PRUEBA
    sectores = {}
    for nombre in ["Guardia Pediatrica", "Cirugia General", "Terapia Intensiva"]:
        s = Sector.obtener_por_nombre(nombre) if hasattr(Sector, "obtener_por_nombre") else None
        if not s:
            s = db.session.scalar(select(Sector).where(Sector.nombre == nombre))
        if not s:
            s = Sector(nombre=nombre, activo=True)
            db.session.add(s)
        sectores[nombre] = s

    db.session.flush()

    # 5. USUARIOS PARA CADA ROL
    pass_hash = hashear_password("Password123!")

    usuarios_data = [
        {
            "email": "admin@hospital.com",
            "nombre": "Esteban",
            "apellido": "Admin",
            "dni": "10000001",
            "rol_id": roles[NombreRol.ADMINISTRADOR.value].id,
            "sector_id": None,
        },
        {
            "email": "alimentacion@hospital.com",
            "nombre": "Carla",
            "apellido": "Dietista",
            "dni": "20000001",
            "rol_id": roles[NombreRol.ALIMENTACION.value].id,
            "sector_id": None,
        },
        {
            "email": "jefe.guardia@hospital.com",
            "nombre": "Martin",
            "apellido": "Gomez",
            "dni": "30000001",
            "rol_id": roles[NombreRol.JEFE_SERVICIO.value].id,
            "sector_id": sectores["Guardia Pediatrica"].id,
        },
        {
            "email": "jefe.cirugia@hospital.com",
            "nombre": "Laura",
            "apellido": "Fernandez",
            "dni": "30000002",
            "rol_id": roles[NombreRol.JEFE_SERVICIO.value].id,
            "sector_id": sectores["Cirugia General"].id,
        },
        {
            "email": "comedor@hospital.com",
            "nombre": "Roberto",
            "apellido": "Comedor",
            "dni": "40000001",
            "rol_id": roles[NombreRol.COMEDOR.value].id,
            "sector_id": None,
        },
        {
            "email": "inactivo@hospital.com",
            "nombre": "Inactivo",
            "apellido": "Bloqueado",
            "dni": "50000001",
            "rol_id": roles[NombreRol.JEFE_SERVICIO.value].id,
            "sector_id": sectores["Terapia Intensiva"].id,
            "activo": False,
        },
    ]

    usuarios = {}
    for u_info in usuarios_data:
        u = User.obtener_por_email(u_info["email"])
        if not u:
            u = User(
                email=u_info["email"],
                nombre=u_info["nombre"],
                apellido=u_info["apellido"],
                dni=u_info["dni"],
                password=pass_hash,
                activo=u_info.get("activo", True),
                rol_id=u_info["rol_id"],
                sector_id=u_info["sector_id"],
            )
            db.session.add(u)
        usuarios[u_info["email"]] = u

    db.session.flush()

    # 6. PERSONAL / COMENSALES
    personal_data = [
        # Guardia Pediatrica
        {"dni": "50001", "nombre": "Juan", "apellido": "Perez", "tipo_id": tipos_personal["Personal Fijo"].id, "sec_id": sectores["Guardia Pediatrica"].id, "m_id": tipos_menu["General"].id},
        {"dni": "50002", "nombre": "Ana", "apellido": "Lopez", "tipo_id": tipos_personal["Personal Fijo"].id, "sec_id": sectores["Guardia Pediatrica"].id, "m_id": tipos_menu["Celíaco"].id},
        {"dni": "50003", "nombre": "Carlos", "apellido": "Ruiz", "tipo_id": tipos_personal["Personal Fijo"].id, "sec_id": sectores["Guardia Pediatrica"].id, "m_id": tipos_menu["Vegetariano"].id},
        # Cirugía General
        {"dni": "50004", "nombre": "Mariana", "apellido": "Diaz", "tipo_id": tipos_personal["Personal Fijo"].id, "sec_id": sectores["Cirugia General"].id, "m_id": tipos_menu["General"].id},
        {"dni": "50005", "nombre": "Tomas", "apellido": "Suarez", "tipo_id": tipos_personal["Personal Fijo"].id, "sec_id": sectores["Cirugia General"].id, "m_id": tipos_menu["Vegetariano"].id},
        # Residente rotante
        {"dni": "50006", "nombre": "Sofia", "apellido": "Residente", "tipo_id": tipos_personal["Residente"].id, "sec_id": None, "m_id": tipos_menu["General"].id},
    ]

    personas = {}
    for p_info in personal_data:
        p = Personal.obtener_por_dni(p_info["dni"])
        if not p:
            p = Personal(
                dni=p_info["dni"],
                nombre=p_info["nombre"],
                apellido=p_info["apellido"],
                tipo_personal_id=p_info["tipo_id"],
                sector_id=p_info["sec_id"],
                menu_id=p_info["m_id"],
                activo=True,
            )
            db.session.add(p)
        personas[p_info["dni"]] = p

    db.session.flush()

    # 7. PEDIDOS Y SOLICITUDES (VARIOS DÍAS, COMIDAS Y ESTADOS)
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    pedidos_simulados = [
        # Pedido 1: Guardia - Ayer
        {
            "sector": sectores["Guardia Pediatrica"],
            "fecha": ayer,
            "estado": "autorizado",
            "creador": usuarios["jefe.guardia@hospital.com"],
            "solicitudes": [
                {"persona": personas["50001"], "comida": "almuerzo", "menu": tipos_menu["General"], "estado": "autorizado"},
                {"persona": personas["50002"], "comida": "almuerzo", "menu": tipos_menu["Celíaco"], "estado": "autorizado"},
                {"persona": personas["50003"], "comida": "cena", "menu": tipos_menu["Vegetariano"], "estado": "autorizado"},
                {"persona": personas["50006"], "comida": "cena", "menu": tipos_menu["General"], "estado": "rechazado"},
            ]
        },
        # Pedido 2: Guardia - Hoy
        {
            "sector": sectores["Guardia Pediatrica"],
            "fecha": hoy,
            "estado": "autorizado",
            "creador": usuarios["jefe.guardia@hospital.com"],
            "solicitudes": [
                {"persona": personas["50001"], "comida": "almuerzo", "menu": tipos_menu["General"], "estado": "autorizado"},
                {"persona": personas["50003"], "comida": "almuerzo", "menu": tipos_menu["Vegetariano"], "estado": "pendiente"},
            ]
        },
        # Pedido 3: Cirugía - Hoy
        {
            "sector": sectores["Cirugia General"],
            "fecha": hoy,
            "estado": "autorizado",
            "creador": usuarios["jefe.cirugia@hospital.com"],
            "solicitudes": [
                {"persona": personas["50004"], "comida": "almuerzo", "menu": tipos_menu["General"], "estado": "autorizado"},
                {"persona": personas["50005"], "comida": "cena", "menu": tipos_menu["Vegetariano"], "estado": "autorizado"},
            ]
        }
    ]

    solicitudes_autorizadas_para_entrega = []

    for ped_info in pedidos_simulados:
        pedido = Pedido.obtener_por_sector_y_fecha(ped_info["sector"].id, ped_info["fecha"])
        if not pedido:
            pedido = Pedido(
                sector_id=ped_info["sector"].id,
                fecha=ped_info["fecha"],
                estado=ped_info["estado"],
                created_by_id=ped_info["creador"].id,
            )
            db.session.add(pedido)
            db.session.flush()

            for sol in ped_info["solicitudes"]:
                solicitud = SolicitudDetalle(
                    pedido_id=pedido.id,
                    person_id=sol["persona"].id,
                    tipo_comida=sol["comida"],
                    tipo_menu_id=sol["menu"].id,
                    condicion="regular",
                    estado_autorizacion=sol["estado"],
                )
                db.session.add(solicitud)
                db.session.flush()

                if sol["estado"] == "autorizado":
                    solicitudes_autorizadas_para_entrega.append(solicitud)

    db.session.flush()

    # 8. ENTREGAS EN COMEDOR
    # Registramos entregas de SOLO algunas viandas para que haya diferencia numérica entre autorizadas y entregadas
    usuario_comedor = usuarios["comedor@hospital.com"]
    
    if solicitudes_autorizadas_para_entrega:
        # Entrega de prueba 1 (retira Juan Perez)
        s1 = solicitudes_autorizadas_para_entrega[0]
        if not EntregaDetalle.existe_por_solicitud(s1.id):
            e1 = Entrega(
                usuario_comedor_id=usuario_comedor.id,
                responsable_retiro="Juan Perez",
                fecha_hora=datetime.now() - timedelta(hours=3),
            )
            db.session.add(e1)
            db.session.flush()
            db.session.add(EntregaDetalle(
                entrega_id=e1.id,
                solicitud_detalle_id=s1.id,
                tipo_menu_entregado_id=s1.tipo_menu_id,
            ))

        # Entrega de prueba 2 si hay más
        if len(solicitudes_autorizadas_para_entrega) > 1:
            s2 = solicitudes_autorizadas_para_entrega[1]
            if not EntregaDetalle.existe_por_solicitud(s2.id):
                e2 = Entrega(
                    usuario_comedor_id=usuario_comedor.id,
                    responsable_retiro="Responsable de Turno Guardia",
                    fecha_hora=datetime.now() - timedelta(hours=1),
                )
                db.session.add(e2)
                db.session.flush()
                db.session.add(EntregaDetalle(
                    entrega_id=e2.id,
                    solicitud_detalle_id=s2.id,
                    tipo_menu_entregado_id=s2.tipo_menu_id,
                ))

    db.session.commit()
    print("Seed de Testing completada exitosamente!")