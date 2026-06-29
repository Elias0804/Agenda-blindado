from flask import Blueprint, request, render_template, redirect, url_for, flash, session, send_file
from datetime import datetime, timedelta
import csv
import io
import os
from db import get_user_db

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")

# ==================== Listar e criar agendamentos ====================
@schedule_bp.route("/", methods=["GET", "POST"])
def schedule():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()

    # Buscar dados para selects
    clients = conn.execute("SELECT id, name FROM clients").fetchall()
    professionals = conn.execute("SELECT id, name FROM professionals").fetchall()
    services = conn.execute("SELECT * FROM services").fetchall()

    # Mapeamento produtos por serviço
    service_products = {}
    for s in services:
        products = conn.execute(
            """
            SELECT sp.product_id AS id, i.name
            FROM service_products sp
            JOIN inventory i ON sp.product_id = i.id
            WHERE sp.service_id=?
            """,
            (s["id"],)
        ).fetchall()
        service_products[s["id"]] = products

    # Criar agendamento
    if request.method == "POST":
        client_id = request.form["client_id"]
        professional_id = request.form["professional_id"]
        service_id = request.form["service_id"]
        date = request.form["date"]
        time = request.form["time"]
        notes = request.form.get("notes", "")

        # Obter informações do serviço
        service = conn.execute(
            "SELECT name, price, duration FROM services WHERE id=?",
            (service_id,),
        ).fetchone()

        if not service:
            flash("Serviço inválido!", "error")
            return redirect(url_for("schedule.schedule"))

        date_time = f"{date} {time}:00"

        # Checar duplicidade: mesmo profissional no mesmo horário
        existing = conn.execute(
            """
            SELECT * FROM schedules
            WHERE professional_id=? AND date_time BETWEEN ? AND ?
            """,
            (professional_id, date_time, date_time),
        ).fetchone()
        if existing:
            flash("Já existe um agendamento neste horário para este profissional!", "error")
            return redirect(url_for("schedule.schedule"))

        # Inserir agendamento
        cur.execute(
            """
            INSERT INTO schedules (client_id, professional_id, service_id, date_time, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (client_id, professional_id, service_id, date_time, notes),
        )
        schedule_id = cur.lastrowid

        # Produtos usados
        for prod in service_products.get(service_id, []):
            qty = float(request.form.get(f"product_{prod['id']}", 0))
            if qty > 0:
                conn.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE id=?",
                    (qty, prod["id"]),
                )
                conn.execute(
                    """
                    INSERT INTO schedule_products (schedule_id, product_id, quantity_used)
                    VALUES (?, ?, ?)
                    """,
                    (schedule_id, prod["id"], qty),
                )

        # Registrar entrada financeira
        conn.execute(
            """
            INSERT INTO finance (date, professional_id, service_id, amount, type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date_time,
                professional_id,
                service_id,
                service["price"] or 0,
                "entrada",
            ),
        )

        conn.commit()
        flash("Agendamento criado com sucesso!", "success")
        return redirect(url_for("schedule.schedule"))

    # Filtrar agendamentos por data
    filter_date = request.args.get("filter_date", "")
    if filter_date:
        schedule_data = conn.execute(
            """
            SELECT s.id, c.name AS client_name, p.name AS professional_name,
                   s.date_time, sv.name AS service_name, sv.price, s.notes
            FROM schedules s
            JOIN clients c ON c.id = s.client_id
            JOIN professionals p ON p.id = s.professional_id
            JOIN services sv ON sv.id = s.service_id
            WHERE date(s.date_time) = ?
            ORDER BY s.date_time
            """,
            (filter_date,),
        ).fetchall()
    else:
        schedule_data = conn.execute(
            """
            SELECT s.id, c.name AS client_name, p.name AS professional_name,
                   s.date_time, sv.name AS service_name, sv.price, s.notes
            FROM schedules s
            JOIN clients c ON c.id = s.client_id
            JOIN professionals p ON p.id = s.professional_id
            JOIN services sv ON sv.id = s.service_id
            ORDER BY s.date_time
            """
        ).fetchall()

    # Buscar produtos usados em cada agendamento
    schedule_products = {}
    for sched in schedule_data:
        prods = conn.execute(
            """
            SELECT i.name, sp.quantity_used
            FROM schedule_products sp
            JOIN inventory i ON i.id = sp.product_id
            WHERE sp.schedule_id = ?
            """,
            (sched["id"],),
        ).fetchall()
        schedule_products[sched["id"]] = prods

    conn.close()
    return render_template(
        "schedule.html",
        clients=clients,
        professionals=professionals,
        services=services,
        service_products=service_products,
        schedule=schedule_data,
        schedule_products=schedule_products,
        filter_date=filter_date,
    )

# ==================== Download dos agendamentos ====================
@schedule_bp.route("/download_weekly")
def download_weekly_schedule():
    conn = get_user_db()
    cur = conn.cursor()

    today = datetime.today().date()
    week_later = today + timedelta(days=7)

    rows = conn.execute(
        """
        SELECT s.id, c.name AS client_name, p.name AS professional_name,
               s.date_time, sv.name AS service_name, sv.price, s.notes
        FROM schedules s
        JOIN clients c ON c.id = s.client_id
        JOIN professionals p ON p.id = s.professional_id
        JOIN services sv ON sv.id = s.service_id
        WHERE date(s.date_time) BETWEEN ? AND ?
        ORDER BY s.date_time
        """,
        (today, week_later),
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Cliente", "Profissional", "Data", "Hora", "Serviço", "Preço", "Observações"])
    for row in rows:
        date_str, time_str = row["date_time"].split(" ")
        writer.writerow([row["client_name"], row["professional_name"], date_str, time_str, row["service_name"], row["price"], row["notes"]])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='agendamento_semanal.csv')

@schedule_bp.route("/download_all")
def download_all_schedule():
    conn = get_user_db()
    cur = conn.cursor()

    rows = conn.execute(
        """
        SELECT s.id, c.name AS client_name, p.name AS professional_name,
               s.date_time, sv.name AS service_name, sv.price, s.notes
        FROM schedules s
        JOIN clients c ON c.id = s.client_id
        JOIN professionals p ON p.id = s.professional_id
        JOIN services sv ON sv.id = s.service_id
        ORDER BY s.date_time
        """
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Cliente", "Profissional", "Data", "Hora", "Serviço", "Preço", "Observações"])
    for row in rows:
        date_str, time_str = row["date_time"].split(" ")
        writer.writerow([row["client_name"], row["professional_name"], date_str, time_str, row["service_name"], row["price"], row["notes"]])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='todos_agendamentos.csv')

# ==================== Editar agendamento ====================
@schedule_bp.route("/edit/<int:schedule_id>", methods=["GET", "POST"])
def edit_schedule(schedule_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()

    sched = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
    if not sched:
        flash("Agendamento não encontrado.", "error")
        conn.close()
        return redirect(url_for("schedule.schedule"))

    clients = conn.execute("SELECT id, name FROM clients").fetchall()
    professionals = conn.execute("SELECT id, name FROM professionals").fetchall()
    services = conn.execute("SELECT * FROM services").fetchall()

    service_products = {}
    for s in services:
        products = conn.execute(
            """
            SELECT sp.product_id AS id, i.name
            FROM service_products sp
            JOIN inventory i ON sp.product_id = i.id
            WHERE sp.service_id = ?
            """,
            (s["id"],)
        ).fetchall()
        service_products[s["id"]] = products

    if request.method == "POST":
        client_id = request.form["client_id"]
        professional_id = request.form["professional_id"]
        service_id = request.form["service_id"]
        date = request.form["date"]
        time = request.form["time"]
        notes = request.form.get("notes", "")

        date_time = f"{date} {time}:00"

        cur.execute(
            """
            UPDATE schedules
            SET client_id=?, professional_id=?, service_id=?, date_time=?, notes=?
            WHERE id=?
            """,
            (client_id, professional_id, service_id, date_time, notes, schedule_id)
        )

        cur.execute("DELETE FROM schedule_products WHERE schedule_id=?", (schedule_id,))
        for prod in service_products.get(int(service_id), []):
            qty = float(request.form.get(f"product_{prod['id']}", 0))
            if qty > 0:
                conn.execute(
                    """
                    INSERT INTO schedule_products (schedule_id, product_id, quantity_used)
                    VALUES (?, ?, ?)
                    """,
                    (schedule_id, prod["id"], qty)
                )

        conn.commit()
        conn.close()
        flash("Agendamento atualizado com sucesso!", "success")
        return redirect(url_for("schedule.schedule"))

    sched_date, sched_time = sched["date_time"].split(" ")
    conn.close()
    return render_template(
        "schedule_edit.html",
        sched=sched,
        sched_date=sched_date,
        sched_time=sched_time,
        clients=clients,
        professionals=professionals,
        services=services,
        service_products=service_products
    )

# ==================== Deletar agendamento ====================
@schedule_bp.route("/delete/<int:schedule_id>", methods=["POST"])
def delete_schedule(schedule_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    conn.execute("DELETE FROM schedule_products WHERE schedule_id=?", (schedule_id,))
    conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()
    flash("Agendamento excluído com sucesso!", "success")
    return redirect(url_for("schedule.schedule"))
