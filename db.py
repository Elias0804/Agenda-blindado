# db.py
import os
import sqlite3
from flask import g, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DB = os.path.join(BASE_DIR, "users.db")        # banco central (login)
USER_DB_DIR = os.path.join(BASE_DIR, "user_dbs")    # pastas dos bancos individuais

def ensure_user_db_dir():
    """Garante que a pasta onde ficam os bancos individuais exista."""
    os.makedirs(USER_DB_DIR, exist_ok=True)

def sanitize_filename(s):
    """Evita caracteres inválidos no nome do arquivo do banco."""
    s = str(s)
    return "".join(c for c in s if c.isalnum() or c in ("-", "_")).strip()

# ------------------ AUTH DB (Login Central) ------------------
def get_auth_db():
    if not hasattr(g, "auth_db"):
        conn = sqlite3.connect(AUTH_DB)
        conn.row_factory = sqlite3.Row
        g.auth_db = conn
    return g.auth_db

def init_auth_db():
    """Cria a tabela de usuários."""
    conn = sqlite3.connect(AUTH_DB)
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """)
        conn.commit()
    finally:
        conn.close()

# ------------------ USER DB (Banco Individual por Usuário) ------------------

def user_db_path(user_id):
    """Retorna o caminho do banco de dados do usuário logado."""
    fname = f"agenda_{sanitize_filename(user_id)}.db"
    return os.path.join(USER_DB_DIR, fname)

def init_user_db(conn):
    """Cria todas as tabelas do banco do usuário."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        duration INTEGER NOT NULL,
        promotion INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        service_id INTEGER,
        date_time TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(service_id) REFERENCES services(id)
    )
    """)

    conn.commit()

def get_user_db():
    """Retorna a conexão com o banco individual do usuário logado."""
    if "user_id" not in session:
        raise RuntimeError("Usuário não está logado — nenhuma base individual pode ser carregada.")

    if not hasattr(g, "user_db"):
        ensure_user_db_dir()
        path = user_db_path(session["user_id"])
        first_creation = not os.path.exists(path)

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row

        # guarda em g
        g.user_db = conn

        # cria tabelas se for novo
        if first_creation:
            init_user_db(conn)

    return g.user_db

# ------------------ Fechamento das conexões ------------------

def close_dbs(e=None):
    """Fecha todos os bancos abertos no contexto do Flask."""
    auth = g.pop("auth_db", None)
    if auth:
        auth.close()

    userdb = g.pop("user_db", None)
    if userdb:
        userdb.close()
