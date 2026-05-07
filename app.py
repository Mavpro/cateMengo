"""
LUMEN - Sistema de Tasación Inmobiliaria - Versión Web
Flask app para Railway/Render
"""
import os, json, io
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_file, jsonify)
from db.database import init_db, authenticate, get_user, create_user, update_user, \
    change_password, get_all_users, delete_user, save_tasacion, update_tasacion, \
    get_tasaciones, get_tasacion, delete_tasacion
from modules.tasacion_logic import calcular_tasacion
from modules.pdf_generator import generate_pdf

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lumen-tasacion-secret-2024")

# Inicializar base de datos al arrancar
with app.app_context():
    init_db()

# ── AUTH ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        user = get_user(session["user_id"])
        if not user or user.get("username") != "admin":
            flash("Acceso restringido al administrador.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = authenticate(request.form["username"], request.form["password"])
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            return redirect(url_for("dashboard"))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user(session["user_id"])
    is_admin = user["username"] == "admin"
    tasaciones = get_tasaciones(None if is_admin else session["user_id"])
    return render_template("dashboard.html", user=user, tasaciones=tasaciones, is_admin=is_admin)

@app.route("/tasacion/nueva", methods=["GET", "POST"])
@login_required
def nueva_tasacion():
    if request.method == "POST":
        data = _parse_form(request.form)
        resultado = calcular_tasacion(
            data["metros2"], data["estado_edilicio"],
            data["ubicacion"], data["comparables"]
        )
        data["resultado"] = resultado
        tid = save_tasacion(session["user_id"], data)
        flash("Tasación guardada correctamente.", "success")
        return redirect(url_for("ver_tasacion", tid=tid))
    return render_template("tasacion_form.html", data=None, title="Nueva Tasación")

@app.route("/tasacion/<int:tid>")
@login_required
def ver_tasacion(tid):
    t = get_tasacion(tid)
    if not t:
        flash("Tasación no encontrada.", "danger")
        return redirect(url_for("dashboard"))
    return render_template("tasacion_ver.html", t=t)

@app.route("/tasacion/<int:tid>/editar", methods=["GET", "POST"])
@login_required
def editar_tasacion(tid):
    t = get_tasacion(tid)
    if not t:
        flash("Tasación no encontrada.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        data = _parse_form(request.form)
        resultado = calcular_tasacion(
            data["metros2"], data["estado_edilicio"],
            data["ubicacion"], data["comparables"]
        )
        data["resultado"] = resultado
        update_tasacion(tid, data)
        flash("Tasación actualizada.", "success")
        return redirect(url_for("ver_tasacion", tid=tid))
    return render_template("tasacion_form.html", data=t, title="Editar Tasación")

@app.route("/tasacion/<int:tid>/eliminar", methods=["POST"])
@login_required
def eliminar_tasacion(tid):
    delete_tasacion(tid)
    flash("Tasación eliminada.", "success")
    return redirect(url_for("dashboard"))

@app.route("/tasacion/<int:tid>/pdf")
@login_required
def generar_pdf(tid):
    t = get_tasacion(tid)
    if not t:
        flash("Tasación no encontrada.", "danger")
        return redirect(url_for("dashboard"))
    user = get_user(t["user_id"])
    t["agent_name"]  = user.get("full_name", "")
    t["agent_email"] = user.get("email", "")
    t["agent_phone"] = user.get("phone", "")
    buf = io.BytesIO()
    generate_pdf(t, t["resultado"], buf)
    buf.seek(0)
    fname = f"Tasacion_{t.get('direccion','propiedad').replace(' ','_')[:30]}_{tid}.pdf"
    return send_file(buf, as_attachment=True, download_name=fname, mimetype="application/pdf")

@app.route("/api/calcular", methods=["POST"])
@login_required
def api_calcular():
    data = request.get_json()
    resultado = calcular_tasacion(
        float(data["metros2"]),
        int(data["estado_edilicio"]),
        int(data["ubicacion"]),
        data["comparables"]
    )
    return jsonify(resultado)

# ── PERFIL ────────────────────────────────────────────────────────────────────

@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    user = get_user(session["user_id"])
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update":
            update_user(session["user_id"],
                        request.form["full_name"],
                        request.form["email"],
                        request.form["phone"])
            session["full_name"] = request.form["full_name"]
            flash("Perfil actualizado.", "success")
        elif action == "password":
            ok, msg = change_password(session["user_id"],
                                      request.form["old_password"],
                                      request.form["new_password"])
            flash(msg, "success" if ok else "danger")
        return redirect(url_for("perfil"))
    return render_template("perfil.html", user=user)

# ── ADMIN ─────────────────────────────────────────────────────────────────────

@app.route("/admin/usuarios")
@admin_required
def admin_usuarios():
    users = get_all_users()
    return render_template("admin_usuarios.html", users=users)

@app.route("/admin/usuario/nuevo", methods=["GET", "POST"])
@admin_required
def admin_nuevo_usuario():
    if request.method == "POST":
        ok, msg = create_user(
            request.form["username"], request.form["password"],
            request.form["full_name"], request.form["email"], request.form["phone"]
        )
        flash(msg, "success" if ok else "danger")
        if ok:
            return redirect(url_for("admin_usuarios"))
    return render_template("admin_nuevo_usuario.html")

@app.route("/admin/usuario/<int:uid>/eliminar", methods=["POST"])
@admin_required
def admin_eliminar_usuario(uid):
    if uid == session["user_id"]:
        flash("No podés eliminar tu propio usuario.", "danger")
    else:
        delete_user(uid)
        flash("Usuario eliminado.", "success")
    return redirect(url_for("admin_usuarios"))

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _parse_form(form):
    comparables = []
    i = 0
    while f"comp_m2_{i}" in form:
        try:
            comparables.append({
                "link":            form.get(f"comp_link_{i}", ""),
                "metros2":         float(form[f"comp_m2_{i}"]),
                "precio":          float(form[f"comp_precio_{i}"]),
                "estado_edilicio": int(form[f"comp_estado_{i}"]),
                "ubicacion":       int(form[f"comp_ubicacion_{i}"]),
            })
        except (ValueError, KeyError):
            pass
        i += 1
    return {
        "tipo_propiedad":  form.get("tipo_propiedad", ""),
        "direccion":       form.get("direccion", ""),
        "barrio":          form.get("barrio", ""),
        "link_propiedad":  form.get("link_propiedad", ""),
        "fecha":           form.get("fecha", datetime.now().strftime("%d/%m/%Y")),
        "metros2":         float(form.get("metros2", 0)),
        "estado_edilicio": int(form.get("estado_edilicio", 2)),
        "ubicacion":       int(form.get("ubicacion", 2)),
        "notas":           form.get("notas", ""),
        "comparables":     comparables,
    }

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
