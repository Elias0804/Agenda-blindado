from flask import Blueprint, render_template, request, redirect, url_for, session
from db import get_user_db

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")

@finance_bp.route("/", methods=["GET"])
def finance():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()

    # Receber filtros de data, se houver
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    date_filter = ""
    params = []

    if start_date:
        date_filter += " AND date(f.date) >= date(?)"
        params.append(start_date)
    if end_date:
        date_filter += " AND date(f.date) <= date(?)"
        params.append(end_date)

    # Lista de entradas (serviços) filtrada por data, se houver
    rows = cur.execute(
        "SELECT f.id, f.date, f.amount, f.type, p.name as professional_name, s.name as service_name "
        "FROM finance f "
        "LEFT JOIN professionals p ON p.id = f.professional_id "
        "LEFT JOIN services s ON s.id = f.service_id "
        "WHERE 1=1 " + date_filter +
        " ORDER BY f.date DESC",
        params
    ).fetchall()

    # Resumo para o período filtrado
    filtered_summary = None
    filtered_by_professional = None
    if start_date or end_date:
        filtered_summary = cur.execute(
            "SELECT COUNT(*) as total_services, COALESCE(SUM(amount),0) as total_price "
            "FROM finance f WHERE f.type='entrada'" + date_filter,
            params
        ).fetchone()
        filtered_by_professional = cur.execute(
            "SELECT p.name, COUNT(f.id) as total_services, COALESCE(SUM(f.amount), 0) as total_price "
            "FROM finance f "
            "LEFT JOIN professionals p ON p.id = f.professional_id "
            "WHERE f.type='entrada' " + date_filter +
            " GROUP BY p.id, p.name ORDER BY total_price DESC",
            params
        ).fetchall()

    # Totais gerais
    total_summary = cur.execute(
        "SELECT COUNT(*) as total_services, COALESCE(SUM(amount),0) as total_price "
        "FROM finance f WHERE f.type='entrada'",
    ).fetchone()

    # Resumo geral por profissional
    summary_by_professional = cur.execute(
        "SELECT p.name, COUNT(f.id) as total_services, COALESCE(SUM(f.amount), 0) as total_price "
        "FROM finance f "
        "LEFT JOIN professionals p ON p.id = f.professional_id "
        "WHERE f.type='entrada' "
        "GROUP BY p.id, p.name ORDER BY total_price DESC",
    ).fetchall()

    # Hoje
    daily_summary = cur.execute(
        "SELECT COUNT(*) as total_services, COALESCE(SUM(amount),0) as total_price "
        "FROM finance f WHERE f.type='entrada' AND date(f.date)=date('now')"
    ).fetchone()

    # Esta semana
    weekly_summary = cur.execute(
        "SELECT COUNT(*) as total_services, COALESCE(SUM(amount),0) as total_price "
        "FROM finance f WHERE f.type='entrada' AND strftime('%W', f.date)=strftime('%W', 'now')"
    ).fetchone()

    conn.close()

    return render_template(
        "finance.html",
        rows=rows,
        summary_by_professional=summary_by_professional,
        total_summary=total_summary,
        daily_summary=daily_summary,
        weekly_summary=weekly_summary,
        start_date=start_date,
        end_date=end_date,
        filtered_summary=filtered_summary,
        filtered_by_professional=filtered_by_professional
    )
