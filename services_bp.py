from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from db import get_db

services_bp = Blueprint('services', __name__)

@services_bp.route('/services/', methods=['GET', 'POST'])
def services():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    cur = conn.cursor()

    # Adicionar serviço
    if "add" in request.form:
        name = request.form.get("name")
        price = request.form.get("price")
        duration = request.form.get("duration")
        if name and price and duration:
            cur.execute("INSERT INTO services (name, price, duration) VALUES (?, ?, ?)",
                        (name, price, duration))
            conn.commit()
            flash("Serviço adicionado com sucesso!", "success")

    # Atualizar serviço
    elif "update" in request.form:
        service_id = request.form.get("service_id")
        name = request.form.get("name")
        price = request.form.get("price")
        duration = request.form.get("duration")
        if service_id:
            cur.execute("UPDATE services SET name=?, price=?, duration=? WHERE id=?",
                        (name, price, duration, service_id))
            conn.commit()
            flash("Serviço atualizado!", "info")

    # Excluir serviço individual
    elif "delete" in request.form:
        service_id = request.form.get("service_id")
        if service_id:
            cur.execute("DELETE FROM services WHERE id=?", (service_id,))
            conn.commit()
            flash("Serviço excluído!", "success")

    # Excluir todos os serviços
    elif "clear_all" in request.form:
        cur.execute("DELETE FROM services")
        conn.commit()
        flash("Todos os serviços foram excluídos!", "warning")

    # Buscar todos os serviços
    cur.execute("SELECT * FROM services")
    services = cur.fetchall()
    conn.close()

    return render_template('services.html', services=services)
