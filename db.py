import sqlite3

DB = 'agenda.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Criar tabelas
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        notes TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        date_time TEXT,
        service_id INTEGER,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        cost REAL
    )''')

    # Seed inicial
    cur.execute('SELECT COUNT(*) as c FROM users')
    if cur.fetchone()['c'] == 0:
        from werkzeug.security import generate_password_hash
        pw = generate_password_hash('admin')
        cur.execute('INSERT INTO users (username, password_hash) VALUES (?,?)', ('admin', pw))

    cur.execute('SELECT COUNT(*) as c FROM services')
    if cur.fetchone()['c'] == 0:
        sample = [
            ('Corte de cabelo', 50.0, 20.0),
            ('Penteado', 80.0, 25.0),
            ('Manicure', 40.0, 10.0)
        ]
        cur.executemany('INSERT INTO services (name, price, cost) VALUES (?,?,?)', sample)

    conn.commit()
    conn.close()
