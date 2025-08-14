from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from db import get_db
from datetime import datetime

schedules_bp = Blueprint('schedules', __name__, url_prefix='/schedule')

@schedules_bp.route('/', methods=['GET','POST'])
def schedule():
    if not session.get('user'):
        return redirect(url_for('auth.login'))
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        client_id = request.form['client_id']
        date_time = request.form['date_time']  # expected YYYY-MM-DD HH:MM
        service_id = request.form['service_id']
        notes = request.form['notes']
        try:
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
    cur.execute('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                   FROM schedules s
                   LEFT JOIN clients c ON c.id = s.client_id
                   LEFT JOIN services sv ON sv.id = s.service_id
                   ORDER BY s.date_time DESC''')
    schedules = cur.fetchall()
    conn.close()
    return render_template('schedule.html', clients=clients, services=services, schedules=schedules)
