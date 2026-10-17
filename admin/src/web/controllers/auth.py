from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.core.auth import autenticar_usuario
from src.core.roles import NombreRol
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/login")
def login_get():
    """Muestra el formulario de inicio de sesión."""
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template("auth/login.html")


@auth_bp.post("/login")
def login_post():
    """Procesa el formulario de login y autentica al usuario."""
    email = request.form.get("email", "")
    password = request.form.get("password", "")

    usuario, error = autenticar_usuario(email, password)

    if error:
        flash(error, "danger")
        return render_template("auth/login.html", email=email), 401

    # Regla propia del panel de administración web
    if not usuario.rol or usuario.rol.nombre != NombreRol.ADMINISTRADOR.value:
        flash("No tiene permisos para acceder al panel de administración.", "danger")
        return render_template("auth/login.html", email=email), 403


    # Manejo manual de sesión sin Flask-Login
    session.clear()
    session.permanent = True  # <-- Activa el temporizador de PERMANENT_SESSION_LIFETIME
    session["user_id"] = usuario.id
    session["user_email"] = usuario.email
    session["user_nombre"] = f"{usuario.nombre} {usuario.apellido}"
    session["user_rol_id"] = usuario.rol_id
    session["user_role"] = usuario.rol.nombre  # Para poder mostrarlo o verificarlo
    session["sector_id"] = usuario.sector_id   # Relevante para Jefe de Servicio

    flash(f"¡Bienvenido/a, {usuario.nombre}!", "success")
    return redirect(url_for("home"))


@auth_bp.get("/logout")
def logout():
    """Cierra la sesión del usuario actual."""
    session.clear()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for("auth.login_get"))



