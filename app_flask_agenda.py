from flask import Flask, request, redirect, url_for, session, render_template_string, send_file, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import io

app = Flask(__name__)
app.secret_key = "troque_esta_chave_por_uma_secreta"  # Mudar em produção
DB = 'agenda.db'

# --- Helpers
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Users
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )''')
    # Clients
    cur.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        notes TEXT
    )''')
    # Professionals
    cur.execute('''CREATE TABLE IF NOT EXISTS professionals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        specialty TEXT
    )''')
    # Services
    cur.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        cost REAL
    )''')
    # Schedules (agendamentos)
    cur.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        professional_id INTEGER,
        service_id INTEGER,
        date_time TEXT,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(professional_id) REFERENCES professionals(id),
        FOREIGN KEY(service_id) REFERENCES services(id)
    )''')
    conn.commit()
    # Seed inicial
    cur.execute('SELECT COUNT(*) as c FROM users')
    if cur.fetchone()['c'] == 0:
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
    cur.execute('SELECT COUNT(*) as c FROM professionals')
    if cur.fetchone()['c'] == 0:
        profs = [
            ('João', '11999999999', 'Cabeleireiro'),
            ('Maria', '11988888888', 'Manicure')
        ]
        cur.executemany('INSERT INTO professionals (name, phone, specialty) VALUES (?,?,?)', profs)
    conn.commit()
    conn.close()

# Inicializa DB
init_db()

# --- Templates base
base = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{title}}</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 2rem auto; padding: 1rem; }
    input, select, textarea { display:block; margin: .5rem 0 1rem; padding: .5rem; width:100%; max-width:400px }
    label { font-weight: bold }
    nav a { margin-right: 1rem }
    table { border-collapse: collapse; width:100%; margin-top:1rem }
    th, td { border: 1px solid #ddd; padding: .5rem }
    .flash { color: darkred }
  </style>
</head>
<body>
  <nav>
    {% if session.get('user') %}
      <a href="{{url_for('dashboard')}}">Dashboard</a>
      <a href="{{url_for('clients')}}">Clientes</a>
      <a href="{{url_for('professionals')}}">Profissionais</a>
      <a href="{{url_for('schedule')}}">Agendamentos</a>
      <a href="{{url_for('services')}}">Preços</a>
      <a href="{{url_for('export_excel')}}">Exportar</a>
      <a href="{{url_for('logout')}}">Sair</a>
    {% else %}
      <a href="{{url_for('login')}}">Login</a>
    {% endif %}
  </nav>
  <h1>{{title}}</h1>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="flash">{% for m in messages %}{{m}}<br>{% endfor %}</div>
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</body>
</html>
'''

# --- Rotas auth
@app.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos')
    tpl = '{% extends base %}{% block content %}<form method="post"><label>Usuário</label><input name="username" required><label>Senha</label><input name="password" type="password" required><button>Entrar</button></form>{% endblock %}'
    return render_template_string(tpl, base=base, title='Login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Dashboard
@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as c FROM clients')
    clients_count = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) as c FROM schedules')
    sched_count = cur.fetchone()['c']
    conn.close()
    tpl = '{% extends base %}{% block content %}<p>Bem-vindo, {{session.user}}</p><p>Clientes cadastrados: {{clients_count}}</p><p>Agendamentos: {{sched_count}}</p>{% endblock %}'
    return render_template_string(tpl, base=base, title='Dashboard', clients_count=clients_count, sched_count=sched_count)

# --- Clients
@app.route('/clients', methods=['GET','POST'])
def clients():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute('INSERT INTO clients (name, phone, email, notes) VALUES (?,?,?,?)',
                    (request.form['name'], request.form['phone'], request.form['email'], request.form['notes']))
        conn.commit()
        flash('Cliente cadastrado')
    cur.execute('SELECT * FROM clients')
    all_clients = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <form method="post"><label>Nome</label><input name="name" required><label>Telefone</label><input name="phone"><label>Email</label><input name="email"><label>Notas</label><textarea name="notes"></textarea><button>Cadastrar</button></form>
    <h3>Clientes</h3>
    <table><tr><th>Nome</th><th>Telefone</th><th>Email</th><th>Notas</th></tr>
    {% for c in all_clients %}<tr><td>{{c['name']}}</td><td>{{c['phone']}}</td><td>{{c['email']}}</td><td>{{c['notes']}}</td></tr>{% endfor %}
    </table>{% endblock %}'''
    return render_template_string(tpl, base=base, title='Clientes', all_clients=all_clients)

# --- Professionals
@app.route('/professionals', methods=['GET','POST'])
def professionals():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute('INSERT INTO professionals (name, phone, specialty) VALUES (?,?,?)',
                    (request.form['name'], request.form['phone'], request.form['specialty']))
        conn.commit()
        flash('Profissional cadastrado')
    cur.execute('SELECT * FROM professionals')
    all_profs = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <form method="post"><label>Nome</label><input name="name" required><label>Telefone</label><input name="phone"><label>Especialidade</label><input name="specialty"><button>Cadastrar</button></form>
    <h3>Profissionais</h3>
    <table><tr><th>Nome</th><th>Telefone</th><th>Especialidade</th></tr>
    {% for p in all_profs %}<tr><td>{{p['name']}}</td><td>{{p['phone']}}</td><td>{{p['specialty']}}</td></tr>{% endfor %}
    </table>{% endblock %}'''
    return render_template_string(tpl, base=base, title='Profissionais', all_profs=all_profs)

# --- Scheduling
@app.route('/schedule', methods=['GET','POST'])
def schedule():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        try:
            dt = datetime.strptime(request.form['date_time'], '%Y-%m-%d %H:%M')
            cur.execute('INSERT INTO schedules (client_id, professional_id, service_id, date_time, notes) VALUES (?,?,?,?,?)',
                        (request.form['client_id'], request.form['professional_id'], request.form['service_id'], dt.isoformat(), request.form['notes']))
            conn.commit()
            flash('Agendamento salvo')
        except ValueError:
            flash('Formato de data inválido. Use: YYYY-MM-DD HH:MM')
    cur.execute('SELECT * FROM clients')
    clients = cur.fetchall()
    cur.execute('SELECT * FROM professionals')
    professionals = cur.fetchall()
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    cur.execute('''SELECT s.id, c.name as client_name, p.name as prof_name, sv.name as service_name, sv.price, sv.cost, s.date_time, s.notes
                   FROM schedules s
                   LEFT JOIN clients c ON c.id = s.client_id
                   LEFT JOIN professionals p ON p.id = s.professional_id
                   LEFT JOIN services sv ON sv.id = s.service_id
                   ORDER BY s.date_time DESC''')
    schedules = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <form method="post">
      <label>Cliente</label><select name="client_id">{% for c in clients %}<option value="{{c['id']}}">{{c['name']}}</option>{% endfor %}</select>
      <label>Profissional</label><select name="professional_id">{% for p in professionals %}<option value="{{p['id']}}">{{p['name']}}</option>{% endfor %}</select>
      <label>Serviço</label><select name="service_id">{% for s in services %}<option value="{{s['id']}}">{{s['name']}}</option>{% endfor %}</select>
      <label>Data e Hora (YYYY-MM-DD HH:MM)</label><input name="date_time" required>
      <label>Notas</label><textarea name="notes"></textarea>
      <button>Agendar</button>
    </form>
    <h3>Agendamentos</h3>
    <table><tr><th>Cliente</th><th>Profissional</th><th>Serviço</th><th>Preço</th><th>Custo</th><th>Data</th><th>Notas</th></tr>
    {% for s in schedules %}<tr><td>{{s['client_name']}}</td><td>{{s['prof_name']}}</td><td>{{s['service_name']}}</td><td>{{'%.2f'|format(s['price'])}}</td><td>{{'%.2f'|format(s['cost'])}}</td><td>{{s['date_time']}}</td><td>{{s['notes']}}</td></tr>{% endfor %}
    </table>{% endblock %}'''
    return render_template_string(tpl, base=base, title='Agendamentos', clients=clients, professionals=professionals, services=services, schedules=schedules)

if __name__ == '__main__':
    app.run(debug=True)
