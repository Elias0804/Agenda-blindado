"""
Flask web app single-file (app_flask_agenda.py)

Atualizado para corrigir erro: ModuleNotFoundError: No module named 'micropip'

Causa do problema e solução aplicada:
- Em alguns ambientes (por exemplo Pyodide / PyScript) importar pacotes pesados no topo do módulo (como pandas/openpyxl) pode acionar o gerenciador "micropip" e causar erros quando ele não está disponível.
- Para evitar isso, removi as importações opcionais de pandas/openpyxl do topo e faço importações sob demanda dentro da rota de exportação.
- Se pandas/openpyxl não estiverem disponíveis, o código faz fallback para gerar um arquivo ZIP contendo dois CSVs (clientes e agendamentos) usando apenas a biblioteca padrão — assim o app roda mesmo em ambientes sem pacotes extras.

Dependências recomendadas (opcionais):
- Para exportar diretamente em Excel (.xlsx): pandas e openpyxl
  pip install pandas openpyxl
- Para rodar o app mínimo: flask
  pip install flask

Executar:
  python app_flask_agenda.py

Observação: este é um exemplo didático e pensado para uso local / desenvolvimento.
"""
from flask import Flask, request, redirect, url_for, session, render_template_string, send_file, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import io
from datetime import datetime

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
    # users: id, username, password_hash
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )''')
    # clients: id, name, phone, email, notes
    cur.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        notes TEXT
    )''')
    # schedules: id, client_id, date_time, service_id, notes
    cur.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        date_time TEXT,
        service_id INTEGER,
        notes TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )''')
    # services: id, name, price, cost
    cur.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        cost REAL
    )''')
    conn.commit()
    # seed a default admin and sample services if empty
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
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# --- Templates (usando render_template_string para simplificar)
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
      <a href="{{url_for('schedule')}}">Agendamentos</a>
      <a href="{{url_for('prices')}}">Preços</a>
      <a href="{{url_for('export_excel')}}">Exportar planilha</a>
      <a href="{{url_for('logout')}}">Sair</a>
    {% else %}
      <a href="{{url_for('login')}}">Login</a>
      <a href="{{url_for('register')}}">Cadastrar</a>
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

# --- Auth routes
@app.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], 'password'):
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos')
    tpl = '{% extends base %}{% block content %}\n<form method="post">\n<label>Usuário</label>\n<input name="username" required>\n<label>Senha</label>\n<input name="password" type="password" required>\n<button>Entrar</button>\n</form>{% endblock %}'
    return render_template_string(tpl, base=base, title='Login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pw_hash = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password_hash) VALUES (?,?)', (username, pw_hash))
            conn.commit()
            flash('Usuário cadastrado. Faça login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Usuário já existe')
        finally:
            conn.close()
    tpl = '{% extends base %}{% block content %}\n<form method="post">\n<label>Usuário</label>\n<input name="username" required>\n<label>Senha</label>\n<input name="password" type="password" required>\n<button>Cadastrar</button>\n</form>{% endblock %}'
    return render_template_string(tpl, base=base, title='Cadastrar')

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
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <p>Bem-vindo, {{session.user}}!</p>
    <p>Clientes cadastrados: {{clients_count}}</p>
    <p>Agendamentos: {{sched_count}}</p>
    <h3>Serviços</h3>
    <table>
      <tr><th>Serviço</th><th>Preço</th><th>Custo</th></tr>
      {% for s in services %}
        <tr><td>{{s['name']}}</td><td>R$ {{'%.2f' % s['price']}}</td><td>R$ {{'%.2f' % s['cost']}}</td></tr>
      {% endfor %}
    </table>
    {% endblock %}'''
    return render_template_string(tpl, base=base, title='Dashboard', clients_count=clients_count, sched_count=sched_count, services=services)

# --- Clients
@app.route('/clients', methods=['GET','POST'])
def clients():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        notes = request.form['notes']
        cur.execute('INSERT INTO clients (name, phone, email, notes) VALUES (?,?,?,?)', (name,phone,email,notes))
        conn.commit()
        flash('Cliente cadastrado')
    cur.execute('SELECT * FROM clients')
    all_clients = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <h3>Cadastrar Cliente</h3>
    <form method="post">
      <label>Nome</label><input name="name" required>
      <label>Telefone</label><input name="phone">
      <label>Email</label><input name="email">
      <label>Observações</label><textarea name="notes"></textarea>
      <button>Cadastrar</button>
    </form>
    <h3>Lista de Clientes</h3>
    <table>
      <tr><th>Nome</th><th>Telefone</th><th>Email</th><th>Notas</th></tr>
      {% for c in all_clients %}
        <tr><td>{{c['name']}}</td><td>{{c['phone']}}</td><td>{{c['email']}}</td><td>{{c['notes']}}</td></tr>
      {% endfor %}
    </table>
    {% endblock %}'''
    return render_template_string(tpl, base=base, title='Clientes', all_clients=all_clients)

# --- Scheduling
@app.route('/schedule', methods=['GET','POST'])
def schedule():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        client_id = request.form['client_id']
        date_time = request.form['date_time']  # expected format YYYY-MM-DD HH:MM
        service_id = request.form['service_id']
        notes = request.form['notes']
        # basic validation
        try:
            # store as ISO string
            dt = datetime.strptime(date_time, '%Y-%m-%d %H:%M')
            cur.execute('INSERT INTO schedules (client_id, date_time, service_id, notes) VALUES (?,?,?,?)', (client_id, dt.isoformat(), service_id, notes))
            conn.commit()
            flash('Agendamento salvo')
        except ValueError:
            flash('Formato de data inválido. Use: YYYY-MM-DD HH:MM')
    cur.execute('SELECT * FROM clients')
    clients = cur.fetchall()
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    # list schedules with join
    cur.execute('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                   FROM schedules s
                   LEFT JOIN clients c ON c.id = s.client_id
                   LEFT JOIN services sv ON sv.id = s.service_id
                   ORDER BY s.date_time DESC''')
    schedules = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <h3>Novo Agendamento</h3>
    <form method="post">
      <label>Cliente</label>
      <select name="client_id" required>
        {% for c in clients %}
          <option value="{{c['id']}}">{{c['name']}}</option>
        {% endfor %}
      </select>
      <label>Data e Hora (YYYY-MM-DD HH:MM)</label>
      <input name="date_time" placeholder="2025-08-11 14:30" required>
      <label>Serviço</label>
      <select name="service_id">
        {% for s in services %}
          <option value="{{s['id']}}">{{s['name']}} - R$ {{'%.2f' % s['price']}}</option>
        {% endfor %}
      </select>
      <label>Notas</label><textarea name="notes"></textarea>
      <button>Agendar</button>
    </form>
    <h3>Agendamentos</h3>
    <table>
      <tr><th>Cliente</th><th>Data</th><th>Serviço</th><th>Preço</th><th>Custo</th><th>Notas</th></tr>
      {% for s in schedules %}
        <tr>
          <td>{{s['client_name']}}</td>
          <td>{{s['date_time']}}</td>
          <td>{{s['service_name']}}</td>
          <td>R$ {{'%.2f' % s['price']}}</td>
          <td>R$ {{'%.2f' % s['cost']}}</td>
          <td>{{s['notes']}}</td>
        </tr>
      {% endfor %}
    </table>
    {% endblock %}'''
    return render_template_string(tpl, base=base, title='Agendamentos', clients=clients, services=services, schedules=schedules)

# --- Prices and costs
@app.route('/prices', methods=['GET','POST'])
def prices():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        # supports add new service or update existing
        if 'add' in request.form:
            name = request.form['name']
            price = float(request.form['price'] or 0)
            cost = float(request.form['cost'] or 0)
            cur.execute('INSERT INTO services (name, price, cost) VALUES (?,?,?)', (name, price, cost))
            conn.commit()
            flash('Serviço adicionado')
        elif 'update' in request.form:
            sid = request.form['service_id']
            price = float(request.form['price'] or 0)
            cost = float(request.form['cost'] or 0)
            cur.execute('UPDATE services SET price=?, cost=? WHERE id=?', (price, cost, sid))
            conn.commit()
            flash('Serviço atualizado')
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    conn.close()
    tpl = '''{% extends base %}{% block content %}
    <h3>Serviços</h3>
    <table>
      <tr><th>Nome</th><th>Preço</th><th>Custo</th></tr>
      {% for s in services %}
        <tr><td>{{s['name']}}</td><td>R$ {{'%.2f' % s['price']}}</td><td>R$ {{'%.2f' % s['cost']}}</td></tr>
      {% endfor %}
    </table>
    <h3>Adicionar Serviço</h3>
    <form method="post">
      <input type="hidden" name="add" value="1">
      <label>Nome</label><input name="name" required>
      <label>Preço</label><input name="price" required>
      <label>Custo</label><input name="cost" required>
      <button>Adicionar</button>
    </form>
    <h3>Atualizar Preço/Custo</h3>
    <form method="post">
      <input type="hidden" name="update" value="1">
      <label>Serviço</label>
      <select name="service_id">
        {% for s in services %}
          <option value="{{s['id']}}">{{s['name']}}</option>
        {% endfor %}
      </select>
      <label>Novo Preço</label><input name="price" required>
      <label>Novo Custo</label><input name="cost" required>
      <button>Atualizar</button>
    </form>
    {% endblock %}'''
    return render_template_string(tpl, base=base, title='Preços e Custos', services=services)

# --- Export to Excel (clients + schedules)
@app.route('/export')
def export_excel():
    """
    Tenta exportar para .xlsx usando pandas+openpyxl se disponíveis.
    Caso contrário, gera um arquivo ZIP com dois CSVs (clientes.csv e agendamentos.csv)
    usando apenas a biblioteca padrão.
    """
    if not session.get('user'):
        return redirect(url_for('login'))

    conn = get_db()
    try:
        # Tentar usar pandas/openpyxl (importação local para evitar erro em ambientes sem micropip)
        import pandas as pd
        # pandas import succeeded, agora checar openpyxl ao escrever
        clients_df = pd.read_sql_query('SELECT * FROM clients', conn)
        schedules_df = pd.read_sql_query('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                                           FROM schedules s
                                           LEFT JOIN clients c ON c.id = s.client_id
                                           LEFT JOIN services sv ON sv.id = s.service_id''', conn)
        # normalizar formato de data
        if 'date_time' in schedules_df.columns:
            schedules_df['date_time'] = schedules_df['date_time'].apply(lambda x: x.replace('T',' ') if isinstance(x, str) else x)
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                clients_df.to_excel(writer, index=False, sheet_name='Clientes')
                schedules_df.to_excel(writer, index=False, sheet_name='Agendamentos')
        except Exception as e:
            # se openpyxl não estiver disponível ou der erro, cair no fallback
            raise
        output.seek(0)
        filename = f'planilha_agenda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        # Falha ao usar pandas/openpyxl — usar fallback com CSVs em ZIP
        # (capturamos qualquer Exception para cobrir ModuleNotFoundError, ImportError, e outros erros de escrita)
        try:
            import csv
            import zipfile
            # Obter dados via sqlite3 (já temos a conexão)
            cur = conn.cursor()
            cur.execute('SELECT * FROM clients')
            clients_rows = cur.fetchall()
            clients_cols = [description[0] for description in cur.description]

            cur.execute('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                           FROM schedules s
                           LEFT JOIN clients c ON c.id = s.client_id
                           LEFT JOIN services sv ON sv.id = s.service_id''')
            sched_rows = cur.fetchall()
            sched_cols = [description[0] for description in cur.description]

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                # clientes.csv
                clients_io = io.StringIO()
                writer = csv.writer(clients_io)
                writer.writerow(clients_cols)
                for r in clients_rows:
                    # sqlite3.Row -> treat as sequence
                    writer.writerow([r[col] for col in clients_cols])
                zf.writestr('clientes.csv', clients_io.getvalue())

                # agendamentos.csv
                sched_io = io.StringIO()
                writer = csv.writer(sched_io)
                writer.writerow(sched_cols)
                for r in sched_rows:
                    # substituir 'T' por ' ' em date_time quando for string
                    row = []
                    for col in sched_cols:
                        val = r[col]
                        if col == 'date_time' and isinstance(val, str):
                            val = val.replace('T', ' ')
                        row.append(val)
                    writer.writerow(row)
                zf.writestr('agendamentos.csv', sched_io.getvalue())

            zip_buffer.seek(0)
            filename = f'planilha_agenda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
            return send_file(zip_buffer, download_name=filename, as_attachment=True, mimetype='application/zip')
        except Exception as ee:
            # Em último caso, informar erro ao usuário
            conn.close()
            flash('Erro ao gerar exportação: ' + str(ee))
            return redirect(url_for('dashboard'))
    finally:
        conn.close()




from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agenda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    empresa = db.Column(db.String(150), nullable=False)
    cnpj = db.Column(db.String(14), nullable=False, unique=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha_hash = db.Column(db.String(128), nullable=False)
    plano = db.Column(db.String(50), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

# Inicializa banco (executar 1x para criar o arquivo)
@app.before_first_request
def cria_bd():
    db.create_all()

# Cadastro (apenas mostra formulário)
@app.route('/cadastro', methods=['GET'])
def cadastro():
    return render_template('cadastro.html')

# Pagamento: GET mostra confirmação, POST finaliza cadastro
@app.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    if request.method == 'GET':
        dados = request.args.to_dict()
        return render_template('pagamento.html', dados=dados)

    else:  # POST
        # Recebe dados do form pagamento (simulado)
        empresa = request.form['empresa']
        cnpj = request.form['cnpj']
        username = request.form['username']
        email = request.form['email']
        senha = request.form['senha']
        plano = request.form['plano']

        # Verifica duplicidade
        if Usuario.query.filter((Usuario.cnpj == cnpj) | (Usuario.username == username) | (Usuario.email == email)).first():
            flash('Empresa, usuário ou email já cadastrados.')
            return redirect(url_for('cadastro'))

        # Cria usuário
        novo_usuario = Usuario(
            empresa=empresa,
            cnpj=cnpj,
            username=username,
            email=email,
            plano=plano
        )
        novo_usuario.set_senha(senha)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Faça login.')
        return redirect(url_for('login'))

# Login simples
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        identificador = request.form['identificador']
        senha = request.form['password']

        if identificador.isdigit() and len(identificador) == 14:
            user = Usuario.query.filter_by(cnpj=identificador).first()
        else:
            user = Usuario.query.filter_by(empresa=identificador).first()

        if user and user.checar_senha(senha):
            flash(f'Bem-vindo, {user.username}!')
            # Aqui você inicia a sessão, redireciona para dashboard etc
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas.')
            return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    return "Aqui será seu dashboard - protegido por login"

if __name__ == '__main__':
    app.run(debug=True)



        


if __name__ == '__main__':
    app.run(debug=True, port=5000)
