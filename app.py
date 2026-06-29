import os
import sqlite3
from flask import Flask, Blueprint, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from db import AUTH_DB, init_auth_db, get_user_db, close_dbs

load_dotenv()
# --------------------- Configurações Iniciais ---------------------
app = Flask(__name__)
app.secret_key = "chave-super-secreta"  # troque por algo seguro em produção
app.teardown_appcontext(close_dbs)

# --------------------- Autenticação Blueprint ---------------------
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")

        with sqlite3.connect(AUTH_DB, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cur.fetchone()

        if user and user["password_hash"] and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            session["user"] = user["name"] or user["email"]
            session["is_admin"] = False
            get_user_db()
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Credenciais inválidas", "error")

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        email = request.form.get("email")
        password = request.form.get("password")
        name = request.form.get("name")
        birth_date = request.form.get("birth_date")

        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect(AUTH_DB, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE email = ?", (email,))
                existing_user = cur.fetchone()

                if existing_user:
                    if existing_user["password_hash"] is None:
                        cur.execute(
                            "UPDATE users SET password_hash = ?, name = ?, birth_date = ? WHERE id = ?",
                            (hashed_password, name, birth_date, existing_user["id"]))
                        conn.commit()
                        user_id = existing_user["id"]
                    else:
                        flash("E-mail já registrado. Faça login.", "error")
                        return render_template('register.html')
                else:
                    cur.execute(
                        """
                        INSERT INTO users (email, password_hash, name, birth_date)
                        VALUES (?, ?, ?, ?)
                        """,
                        (email, hashed_password, name, birth_date))
                    user_id = cur.lastrowid
                    conn.commit()

            session["user_id"] = user_id
            session["user_email"] = email
            session["user"] = name or email
            session["is_admin"] = False
            get_user_db()

            return redirect(url_for("auth.dashboard"))
        except sqlite3.IntegrityError:
            flash("E-mail já registrado. Faça login.", "error")

    return render_template('register.html')

@auth_bp.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        flash('Você precisa estar logado.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_user_db()

    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) AS c FROM clients')
    clients_count = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) AS c FROM services')
    services_count = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM schedules WHERE date(date_time) = date('now')")
    today_schedule = cur.fetchone()['c']
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    conn.close()

    return render_template('dashboard.html',
                           clients_count=clients_count,
                           services_count=services_count,
                           today_schedule=today_schedule,
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

import os

def init_oauth(app):
    oauth.init_app(app)

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    print("GOOGLE_CLIENT_ID:", client_id)
    print("GOOGLE_CLIENT_SECRET:", "***" if client_secret else None)

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

    if not email:
        flash('E-mail do Google não foi retornado.', 'error')
        return redirect(url_for('auth.login'))

    with sqlite3.connect(AUTH_DB, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

        if not user:
            cur.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                (email, name, None),
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cur.fetchone()

    session["user_id"] = user["id"]
    session["user_email"] = email
    session["user"] = name
    session["is_admin"] = False
    get_user_db()

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
