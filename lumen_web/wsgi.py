"""
Entry point para Railway - inicializa la DB antes de arrancar
"""
from db.database import init_db
from app import app

init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
