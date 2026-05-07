"""
Database management for LUMEN Tasacion
DB stored in user's AppData so the EXE works standalone on any machine
"""
import sqlite3
import os
import sys
import hashlib
import json
from datetime import datetime


def _get_db_path():
    """Returns a writable DB path regardless of whether running as EXE or script."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller EXE — use AppData/Roaming
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        folder = os.path.join(base, 'LUMEN_Tasacion')
    else:
        # Running as script — use project root/data
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'lumen.db')


DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo_propiedad TEXT,
            direccion TEXT,
            barrio TEXT,
            metros2 REAL NOT NULL,
            estado_edilicio INTEGER NOT NULL,
            ubicacion INTEGER NOT NULL,
            link_propiedad TEXT,
            comparables TEXT,
            resultado TEXT,
            notas TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Default admin user
    existing = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not existing:
        c.execute(
            "INSERT INTO users (username, password_hash, full_name, email, phone) VALUES (?,?,?,?,?)",
            ("admin", hash_password("admin123"), "Administrador", "admin@lumen.com", "")
        )

    conn.commit()
    conn.close()

# ── AUTH ──────────────────────────────────────────────────────────────────────

def authenticate(username: str, password: str):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user(user_id: int):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(username, password, full_name, email="", phone=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, email, phone) VALUES (?,?,?,?,?)",
            (username, hash_password(password), full_name, email, phone)
        )
        conn.commit()
        return True, "Usuario creado correctamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe."
    finally:
        conn.close()

def update_user(user_id, full_name, email, phone):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET full_name=?, email=?, phone=? WHERE id=?",
        (full_name, email, phone, user_id)
    )
    conn.commit()
    conn.close()

def change_password(user_id, old_password, new_password):
    conn = get_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE id=? AND password_hash=?",
        (user_id, hash_password(old_password))
    ).fetchone()
    if not user:
        conn.close()
        return False, "Contraseña actual incorrecta."
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password), user_id)
    )
    conn.commit()
    conn.close()
    return True, "Contraseña actualizada."

def get_all_users():
    conn = get_connection()
    users = conn.execute("SELECT id, username, full_name, email, phone FROM users ORDER BY full_name").fetchall()
    conn.close()
    return [dict(u) for u in users]

def delete_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

# ── CONFIG ────────────────────────────────────────────────────────────────────

def get_config(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_config(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

# ── TASACIONES ────────────────────────────────────────────────────────────────

def save_tasacion(user_id, data: dict) -> int:
    conn = get_connection()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO tasaciones
           (user_id, fecha, tipo_propiedad, direccion, barrio, metros2,
            estado_edilicio, ubicacion, link_propiedad, comparables, resultado, notas, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            user_id,
            data.get("fecha", now[:10]),
            data.get("tipo_propiedad", ""),
            data.get("direccion", ""),
            data.get("barrio", ""),
            data["metros2"],
            data["estado_edilicio"],
            data["ubicacion"],
            data.get("link_propiedad", ""),
            json.dumps(data.get("comparables", [])),
            json.dumps(data.get("resultado", {})),
            data.get("notas", ""),
            now, now
        )
    )
    tid = cursor.lastrowid
    conn.commit()
    conn.close()
    return tid

def update_tasacion(tasacion_id, data: dict):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE tasaciones SET
           fecha=?, tipo_propiedad=?, direccion=?, barrio=?, metros2=?,
           estado_edilicio=?, ubicacion=?, link_propiedad=?, comparables=?,
           resultado=?, notas=?, updated_at=?
           WHERE id=?""",
        (
            data.get("fecha", now[:10]),
            data.get("tipo_propiedad", ""),
            data.get("direccion", ""),
            data.get("barrio", ""),
            data["metros2"],
            data["estado_edilicio"],
            data["ubicacion"],
            data.get("link_propiedad", ""),
            json.dumps(data.get("comparables", [])),
            json.dumps(data.get("resultado", {})),
            data.get("notas", ""),
            now,
            tasacion_id
        )
    )
    conn.commit()
    conn.close()

def get_tasaciones(user_id=None):
    conn = get_connection()
    if user_id:
        rows = conn.execute(
            """SELECT t.*, u.full_name as agent_name FROM tasaciones t
               JOIN users u ON t.user_id=u.id
               WHERE t.user_id=? ORDER BY t.created_at DESC""",
            (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT t.*, u.full_name as agent_name FROM tasaciones t
               JOIN users u ON t.user_id=u.id
               ORDER BY t.created_at DESC"""
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["comparables"] = json.loads(d["comparables"] or "[]")
        d["resultado"] = json.loads(d["resultado"] or "{}")
        result.append(d)
    return result

def get_tasacion(tasacion_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT t.*, u.full_name as agent_name, u.email as agent_email,
                  u.phone as agent_phone
           FROM tasaciones t JOIN users u ON t.user_id=u.id
           WHERE t.id=?""",
        (tasacion_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["comparables"] = json.loads(d["comparables"] or "[]")
    d["resultado"] = json.loads(d["resultado"] or "{}")
    return d

def delete_tasacion(tasacion_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasaciones WHERE id=?", (tasacion_id,))
    conn.commit()
    conn.close()
