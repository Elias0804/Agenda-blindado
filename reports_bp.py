# reports_bp.py

from flask import Blueprint, render_template, render_template_string, session, redirect, url_for
from db import get_user_db

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()

    stats = {}
    stats["total_clients"] = cur.execute("SELECT COUNT(*) AS c FROM clients").fetchone()["c"]
    stats["total_professionals"] = cur.execute("SELECT COUNT(*) AS c FROM professionals").fetchone()["c"]
    stats["total_schedules"] = cur.execute("SELECT COUNT(*) AS c FROM schedules").fetchone()["c"]
    rev = cur.execute("SELECT COALESCE(SUM(amount),0) AS s FROM finance WHERE type='entrada'").fetchone()["s"]
    stats["total_revenue"] = rev or 0

    return render_template("reports.html", stats=stats)


def _render_report(title, rows, headers):
    template = """
    {% extends 'base.html' %}
    {% block title %}{{ title }} - Relatórios{% endblock %}
    {% block header %}{{ title }}{% endblock %}
    {% block content %}
    <h3>{{ title }}</h3>
    <table class='table-card'>
      <thead>
        <tr>{% for h in headers %}<th>{{ h }}</th>{% endfor %}</tr>
      </thead>
      <tbody>
        {% for row in rows %}
          <tr>{% for col in row %}<td>{{ col }}</td>{% endfor %}</tr>
        {% endfor %}
      </tbody>
    </table>
    <p><a href="{{ url_for('reports.index') }}">Voltar aos relatórios</a></p>
    {% endblock %}
    """
    return render_template_string(template, title=title, rows=rows, headers=headers)


@reports_bp.route('/schedules')
def schedules_report():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT s.id, c.name AS client, p.name AS professional, sv.name AS service, s.date_time, s.notes
        FROM schedules s
        LEFT JOIN clients c ON c.id = s.client_id
        LEFT JOIN professionals p ON p.id = s.professional_id
        LEFT JOIN services sv ON sv.id = s.service_id
        ORDER BY s.date_time DESC
        """
    ).fetchall()
    rows = [[r['id'], r['client'], r['professional'], r['service'], r['date_time'], r['notes']] for r in rows]
    headers = ['ID', 'Cliente', 'Profissional', 'Serviço', 'Data/Hora', 'Notas']
    return _render_report('Relatório de Agendamentos', rows, headers)


@reports_bp.route('/finance')
def finance_report():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT f.id, f.date, p.name AS professional, s.name AS service, f.amount, f.type
        FROM finance f
        LEFT JOIN professionals p ON p.id = f.professional_id
        LEFT JOIN services s ON s.id = f.service_id
        ORDER BY f.date DESC
        """
    ).fetchall()
    rows = [[r['id'], r['date'], r['professional'], r['service'], r['amount'], r['type']] for r in rows]
    headers = ['ID', 'Data', 'Profissional', 'Serviço', 'Valor', 'Tipo']
    return _render_report('Relatório Financeiro', rows, headers)


@reports_bp.route('/clients')
def clients_report():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, name, phone, notes FROM clients ORDER BY name").fetchall()
    rows = [[r['id'], r['name'], r['phone'], r['notes']] for r in rows]
    headers = ['ID', 'Cliente', 'Telefone', 'Notas']
    return _render_report('Relatório de Clientes', rows, headers)


@reports_bp.route('/services')
def services_report():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, name, category, price, duration, promotion FROM services ORDER BY name").fetchall()
    rows = [[r['id'], r['name'], r['category'], r['price'], r['duration'], r['promotion']] for r in rows]
    headers = ['ID', 'Serviço', 'Categoria', 'Preço', 'Duração', 'Promoção']
    return _render_report('Relatório de Serviços', rows, headers)
