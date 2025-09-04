import sqlite3
from werkzeug.security import generate_password_hash

DB = 'agenda.db'

# --- Conexão com o banco
def get_db():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# --- Inicialização do banco
def init_db():
    """Cria tabelas e insere dados iniciais se estiverem vazias."""
    conn = get_db()
    cur = conn.cursor()

    # --- Tabela de usuários
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')

    # --- Tabela de clientes
    cur.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        notes TEXT
    )
    ''')

    # --- Tabela de profissionais
    cur.execute('''
    CREATE TABLE IF NOT EXISTS professionals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        specialty TEXT
    )
    ''')

    # --- Tabela de serviços (com duração, sem cost)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        duration INTEGER NOT NULL
    )
    ''')

    # --- Tabela de agendamentos
    cur.execute('''
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
    ''')

    # --- Seed inicial de usuário admin
    cur.execute('SELECT COUNT(*) as c FROM users')
    if cur.fetchone()['c'] == 0:
        pw_hash = generate_password_hash('admin')
        cur.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('admin', pw_hash))
        print("Usuário admin criado: username=admin, senha=admin")

    # --- Seed inicial de serviços
    cur.execute('SELECT COUNT(*) as c FROM services')
    if cur.fetchone()['c'] == 0:
        sample_services = [
            ('Corte de cabelo', 50.0, 30),   # 30 minutos
            ('Penteado', 80.0, 45),         # 45 minutos
            ('Manicure', 40.0, 20)          # 20 minutos
        ]
        cur.executemany('INSERT INTO services (name, price, duration) VALUES (?, ?, ?)', sample_services)
        print("Serviços iniciais adicionados.")

    conn.commit()
    conn.close()
    print("Banco de dados inicializado com sucesso!")

# --- Função auxiliar para limpar o banco (opcional, uso em dev)
def reset_db():
    """Apaga todas as tabelas e reinicia o banco."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS schedules")
    cur.execute("DROP TABLE IF EXISTS services")
    cur.execute("DROP TABLE IF EXISTS professionals")
    cur.execute("DROP TABLE IF EXISTS clients")
    cur.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()
    print("Banco de dados limpo. Rode init_db() para recriar tudo.")
