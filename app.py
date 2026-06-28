import os
import sqlite3
from flask import Flask, Blueprint, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

load_dotenv()
# --------------------- Configurações Iniciais ---------------------
app = Flask(__name__)
app.secret_key = "chave-super-secreta"  # troque por algo seguro em produção

# Caminhos de banco de dados
AUTH_DB = os.path.join(os.getcwd(), "auth_users.db")
USER_DBS_DIR = os.path.join(os.getcwd(), "user_dbs")
os.makedirs(USER_DBS_DIR, exist_ok=True)

# --------------------- Banco de Usuários (Autenticação) ---------------------
def init_auth_db():
    conn = sqlite3.connect(AUTH_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            name TEXT,
            birth_date TEXT
        )""")
    conn.commit()
    conn.close()

# --------------------- Banco de Dados por Usuário ---------------------
def get_user_db():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db_path = os.path.join(USER_DBS_DIR, f"user_{user_id}.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_user_db(user_id):
    conn = get_user_db()
    if conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            duration INTEGER NOT NULL,
            promotion INTEGER DEFAULT 0
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT
        )""")
        conn.commit()
        conn.close()

# --------------------- Autenticação Blueprint ---------------------
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(AUTH_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and user["password"] and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            init_user_db(user["id"])
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Credenciais inválidas", "error")

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")
        birth_date = request.form.get("birth_date")

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect(AUTH_DB)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (email, password, name, birth_date)
                VALUES (?, ?, ?, ?)
                """,
                (email, hashed_password, name, birth_date))
            conn.commit()
            conn.close()
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for("auth.login"))
        except sqlite3.IntegrityError:
            flash("E-mail já registrado.", "error")

    return render_template('register.html')

@auth_bp.route('/dashboard')
def dashboard():
    conn = get_user_db()
    if not conn:
        flash('Você precisa estar logado.', 'error')
        return redirect(url_for('auth.login'))

    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) AS c FROM clients')
    clients_count = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) AS c FROM services')
    services_count = cur.fetchone()['c']
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    conn.close()

    return render_template('dashboard.html',
                           clients_count=clients_count,
                           services_count=services_count,
                           services=services)

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada', 'success')
    return redirect(url_for('auth.login'))

# --------------------- Google OAuth ---------------------
import os

client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not client_id or not client_secret:
    raise RuntimeError(
        "GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET não configurados."
    )

oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)

    print("GOOGLE_CLIENT_ID:", os.getenv("GOOGLE_CLIENT_ID"))
    print("GOOGLE_CLIENT_SECRET:", os.getenv("GOOGLE_CLIENT_SECRET"))

    oauth.register(
    name="google",
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
    


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get('https://openidconnect.googleapis.com/v1/userinfo').json()

    if not user_info:
        flash('Erro ao obter dados do Google', 'error')
        return redirect(url_for('auth.login'))

    email = user_info.get('email')
    name = user_info.get('name', 'Usuário Google')

    conn = sqlite3.connect(AUTH_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    if not user:
        cur.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
    conn.close()

    session["user_id"] = user["id"]
    session["user_email"] = email
    init_user_db(user["id"])

    flash(f'Bem-vindo {name}', 'success')
    return redirect(url_for('auth.dashboard'))

# --------------------- Inicialização ---------------------
init_auth_db()
init_oauth(app)

# --------------------- Registro de Blueprints ---------------------
app.register_blueprint(auth_bp)

# Blueprints separados (importar depois de app pronto)
from clients import clients_bp
from professionals_bp import professionals_bp
from services_bp import services_bp
from schedule_bp import schedule_bp
from finance_bp import finance_bp
from inventory_bp import inventory_bp  # Corrija o caminho conforme sua estrutura
from reports_bp import reports_bp
from admin_bp import admin_bp


app.register_blueprint(admin_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(professionals_bp)
app.register_blueprint(services_bp)
app.register_blueprint(schedule_bp)
app.register_blueprint(finance_bp)

# --------------------- Rota Inicial ---------------------
@app.route("/")
def home():
    return redirect(url_for("auth.login"))

# --------------------- Rodar Servidor ---------------------
if __name__ == "__main__":
    app.run(debug=True)

# --------------------- Debug: Print de Endpoints ---------------------
for rule in app.url_map.iter_rules():
    print("{rule.endpoint}: {rule}")
