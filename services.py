from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from db import get_db

services_bp = Blueprint('services', __name__, url_prefix='/prices')

@services_bp.route('/', methods=['GET','POST'])
def prices():
    if not session.get('user'):
        return redirect(url_for('auth.login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
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
    return render_template('prices.html', services=services)
