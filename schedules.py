from flask import Flask, Blueprint, request, redirect, url_for, session, render_template, flash, send_file
from db import get_db
from datetime import datetime, timedelta
import csv
import io

schedules_bp = Blueprint('schedules', __name__, url_prefix='/schedule')

# =========================
# Listar e criar agendamentos
# =========================
@schedules_bp.route('/', methods=['GET', 'POST'])
def schedule():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()

    # Buscar dados para dropdowns
    clients = cur.execute("SELECT id, name FROM clients").fetchall()
    professionals = cur.execute("SELECT id, name FROM professionals").fetchall()
    services = cur.execute("SELECT id, name, price, duration FROM services").fetchall()

    if request.method == "POST":
        client_id = request.form.get('client_id')
        professional_id = request.form.get('professional_id')
        date = request.form.get('date')
        time = request.form.get('time')
        service_id = request.form.get('service_id')
        notes = request.form.get('notes', '')

        if not client_id or not professional_id or not date or not time or not service_id:
            flash("Preencha todos os campos obrigatórios.", "error")
            return redirect(url_for('schedules.schedule'))

        try:
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Formato de data/hora inválido.", "error")
            return redirect(url_for('schedules.schedule'))

        # Buscar duração do serviço
        service = cur.execute("SELECT duration FROM services WHERE id = ?", (service_id,)).fetchone()
        if not service:
            flash("Serviço inválido.", "error")
            return redirect(url_for('schedules.schedule'))

        duration = service['duration']
        end_datetime = start_datetime + timedelta(minutes=duration)

        # Verificar conflito de horários para o mesmo profissional
        conflict = cur.execute("""
            SELECT s.id FROM schedules s
            JOIN services srv ON s.service_id = srv.id
            WHERE s.professional_id = ?
            AND (
                (datetime(s.date_time) <= ? AND datetime(s.date_time, '+' || srv.duration || ' minutes') > ?)
                OR
                (datetime(s.date_time) < ? AND datetime(s.date_time, '+' || srv.duration || ' minutes') >= ?)
            )
        """, (professional_id, start_datetime, start_datetime, end_datetime, end_datetime)).fetchone()

        if conflict:
            flash("O profissional já possui agendamento nesse horário.", "error")
            return redirect(url_for('schedules.schedule'))

        # Inserir agendamento
        cur.execute("""
            INSERT INTO schedules (client_id, professional_id, date_time, service_id, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (client_id, professional_id, start_datetime, service_id, notes))
        conn.commit()
        flash("Agendamento realizado com sucesso!", "success")
        return redirect(url_for('schedules.schedule'))

    # =========================
    # Filtrar por data (GET)
    # =========================
    filter_date = request.args.get('filter_date')
    filter_start = filter_end = None
    if filter_date:
        try:
            filter_start = datetime.strptime(filter_date, '%Y-%m-%d')
            filter_end = filter_start + timedelta(days=1)
        except ValueError:
            filter_date = None

    # Buscar agendamentos
    query = """
        SELECT s.id, s.client_id, s.professional_id,
               c.name as client_name, p.name as professional_name,
               s.date_time, sv.name as service_name, sv.price, s.notes
        FROM schedules s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN professionals p ON p.id = s.professional_id
        LEFT JOIN services sv ON sv.id = s.service_id
    """
    params = []
    if filter_start and filter_end:
        query += " WHERE s.date_time BETWEEN ? AND ?"
        params = [filter_start.isoformat(), filter_end.isoformat()]
    query += " ORDER BY s.date_time ASC"
    cur.execute(query, params)
    schedules = cur.fetchall()

    conn.close()
    return render_template(
        'schedules.html',
        clients=clients,
        professionals=professionals,
        services=services,
        schedules=schedules,
        filter_date=filter_date
    )


# =========================
# Editar agendamento
# =========================
@schedules_bp.route('/edit/<int:schedule_id>', methods=['GET', 'POST'])
def edit_schedule(schedule_id):
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute('SELECT * FROM schedules WHERE id=?', (schedule_id,))
    sched = cur.fetchone()
    if not sched:
        flash("Agendamento não encontrado.", "error")
        conn.close()
        return redirect(url_for('schedules.schedule'))

    # Dados para selects
    clients = cur.execute("SELECT id, name FROM clients").fetchall()
    professionals = cur.execute("SELECT id, name FROM professionals").fetchall()
    services = cur.execute("SELECT id, name, price, duration FROM services").fetchall()

    if request.method == 'POST':
        client_id = request.form['client_id']
        professional_id = request.form['professional_id']
        date = request.form['date']
        time = request.form['time']
        service_id = request.form['service_id']
        notes = request.form.get('notes', '')

        start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        service = cur.execute("SELECT duration FROM services WHERE id=?", (service_id,)).fetchone()
        duration = service['duration']
        end_datetime = start_datetime + timedelta(minutes=duration)

        # Verificar conflito, ignorando o próprio agendamento
        conflict = cur.execute("""
            SELECT s.id FROM schedules s
            JOIN services srv ON s.service_id = srv.id
            WHERE s.professional_id = ? AND s.id != ?
            AND (
                (datetime(s.date_time) <= ? AND datetime(s.date_time, '+' || srv.duration || ' minutes') > ?)
                OR
                (datetime(s.date_time) < ? AND datetime(s.date_time, '+' || srv.duration || ' minutes') >= ?)
            )
        """, (professional_id, schedule_id, start_datetime, start_datetime, end_datetime, end_datetime)).fetchone()

        if conflict:
            flash("O profissional já possui agendamento nesse horário.", "error")
            return redirect(url_for('schedules.edit_schedule', schedule_id=schedule_id))

        cur.execute("""
            UPDATE schedules
            SET client_id=?, professional_id=?, date_time=?, service_id=?, notes=?
            WHERE id=?
        """, (client_id, professional_id, start_datetime, service_id, notes, schedule_id))
        conn.commit()
        conn.close()
        flash("Agendamento atualizado com sucesso.", "success")
        return redirect(url_for('schedules.schedule'))

    conn.close()
    return render_template(
        'edit_schedule.html',
        sched=sched,
        clients=clients,
        professionals=professionals,
        services=services
    )


# =========================
# Excluir agendamento
# =========================
@schedules_bp.route('/delete/<int:schedule_id>', methods=['POST'])
def delete_schedule(schedule_id):
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()
    flash("Agendamento excluído com sucesso!", "success")
    return redirect(url_for('schedules.schedule'))


# =========================
# Download CSV
# =========================
def generate_csv(rows, headers):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in rows:
        writer.writerow([r[h] if h in r.keys() else '' for h in headers])
    output.seek(0)
    return io.BytesIO(output.getvalue().encode())

@schedules_bp.route('/download_weekly')
def download_weekly_schedule():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    cur.execute("""
        SELECT s.date_time, c.name as client_name, p.name as professional_name,
               sv.name as service_name, sv.price
        FROM schedules s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN professionals p ON p.id = s.professional_id
        LEFT JOIN services sv ON sv.id = s.service_id
        WHERE s.date_time BETWEEN ? AND ?
        ORDER BY s.date_time ASC
    """, (start_date.isoformat(), end_date.isoformat()))
    rows = cur.fetchall()
    conn.close()

    return send_file(
        generate_csv(rows, ['date_time', 'client_name', 'professional_name', 'service_name', 'price']),
        mimetype='text/csv',
        download_name='agenda_semanal.csv',
        as_attachment=True
    )

@schedules_bp.route('/download_all')
def download_all_schedule():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.date_time, c.name as client_name, p.name as professional_name,
               sv.name as service_name, sv.price, s.notes
        FROM schedules s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN professionals p ON p.id = s.professional_id
        LEFT JOIN services sv ON sv.id = s.service_id
        ORDER BY s.date_time ASC
    """)
    rows = cur.fetchall()
    conn.close()

    return send_file(
        generate_csv(rows, ['date_time', 'client_name', 'professional_name', 'service_name', 'price', 'notes']),
        mimetype='text/csv',
        download_name='agenda_completa.csv',
        as_attachment=True
    )
