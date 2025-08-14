from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # <-- capturar username aqui
        password = request.form.get('password')
        
        if not username or not password:
            flash('Preencha usuário e senha')
            return redirect(url_for('auth.login'))

        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
        row = cur.fetchone()
        conn.close()
        
        if row and check_password_hash(row['password_hash'], password):
            session['user'] = username
            return redirect(url_for('auth.dashboard'))
        flash('Usuário ou senha inválidos')
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET','POST'])
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
            return redirect(url_for('auth.login'))
        except Exception:
            flash('Usuário já existe')
        finally:
            conn.close()
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

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
