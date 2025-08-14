from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from db import get_db

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/', methods=['GET','POST'])
def clients():
    if not session.get('user'):
        return redirect(url_for('auth.login'))
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
    return render_template('clients.html', all_clients=all_clients)
