from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth_bp = Blueprint('auth', __name__)

# ---------- LOGIN ----------
@auth_bp.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Preencha usuário e senha', 'error')
            return redirect(url_for('auth.login'))

        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
        row = cur.fetchone()
        conn.close()

        if row and check_password_hash(row['password_hash'], password):
            session['user'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('auth.dashboard'))

        flash('Usuário ou senha inválidos', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')

# ---------- REGISTER ----------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Preencha todos os campos', 'error')
            return redirect(url_for('auth.register'))

        pw_hash = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pw_hash))
            conn.commit()
            flash('Usuário cadastrado com sucesso. Faça login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            flash('Usuário já existe', 'error')
        finally:
            conn.close()

    return render_template('register.html')

# ---------- LOGOUT ----------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sessão.', 'success')
    return redirect(url_for('auth.login'))

# ---------- DASHBOARD ----------
@auth_bp.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as c FROM clients')
    clients_count = cur.fetchone()['c']
    cur.execute('SELECT COUNT(*) as c FROM schedules')
    sched_count = cur.fetchone()['c']
    cur.execute('SELECT * FROM services')
    services = cur.fetchall()
    conn.close()

    return render_template('dashboard.html', clients_count=clients_count, sched_count=sched_count, services=services)

# ---------- ADMIN USERS ----------
@auth_bp.route('/admin/users')
def list_users():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, username FROM users')
    users = cur.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)

@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for('auth.list_users'))

professionals_bp = Blueprint("professionals", __name__)

@professionals_bp.route("/professionals", methods=["GET", "POST"])
def some_function():
    ...
