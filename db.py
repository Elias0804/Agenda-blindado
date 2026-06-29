# db.py
import os
import sqlite3
from flask import g, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DB = os.path.join(BASE_DIR, "auth_users.db")        # banco central (login)
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
    """Cria a tabela de usuários e atualiza o schema quando necessário."""
    conn = sqlite3.connect(AUTH_DB)
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            birth_date TEXT
        )
        """)
        conn.commit()

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]

        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            conn.commit()
            if "password" in columns:
                conn.execute("UPDATE users SET password_hash = password WHERE password IS NOT NULL")
                conn.commit()

        if "birth_date" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN birth_date TEXT")
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
        phone TEXT,
        notes TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        professional_id INTEGER,
        service_id INTEGER,
        date_time TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(professional_id) REFERENCES professionals(id),
        FOREIGN KEY(service_id) REFERENCES services(id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS professionals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        specialty TEXT,
        cpf TEXT,
        cnpj TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        usage_per_service REAL DEFAULT 0,
        min_stock INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS service_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity_used REAL DEFAULT 0,
        FOREIGN KEY(service_id) REFERENCES services(id),
        FOREIGN KEY(product_id) REFERENCES inventory(id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS schedule_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity_used REAL DEFAULT 0,
        FOREIGN KEY(schedule_id) REFERENCES schedules(id),
        FOREIGN KEY(product_id) REFERENCES inventory(id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS finance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        professional_id INTEGER,
        service_id INTEGER,
        amount REAL,
        type TEXT,
        FOREIGN KEY(professional_id) REFERENCES professionals(id),
        FOREIGN KEY(service_id) REFERENCES services(id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS notas_fiscais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT,
        profissional_id INTEGER,
        dono_id INTEGER,
        data_emissao TEXT,
        valor REAL,
        arquivo_pdf TEXT,
        FOREIGN KEY(profissional_id) REFERENCES professionals(id)
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

        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row

        # guarda em g
        g.user_db = conn

        # cria ou atualiza tabelas sempre que necessário
        init_user_db(conn)

        cur = conn.cursor()
        cur.execute("PRAGMA table_info(clients)")
        client_columns = [row[1] for row in cur.fetchall()]
        if "notes" not in client_columns:
            cur.execute("ALTER TABLE clients ADD COLUMN notes TEXT")
            conn.commit()

        cur.execute("PRAGMA table_info(schedules)")
        schedule_columns = [row[1] for row in cur.fetchall()]
        if "professional_id" not in schedule_columns:
            cur.execute("ALTER TABLE schedules ADD COLUMN professional_id INTEGER")
            conn.commit()

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
