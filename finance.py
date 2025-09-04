from flask import Blueprint, render_template, request
from db import get_db
from datetime import datetime, date, timedelta

finance_bp = Blueprint('finance_bp', __name__)

@finance_bp.route("/finance", methods=["GET"])
def summary():
    conn = get_db()
    cur = conn.cursor()

    # --- Data atual
    now = datetime.now()

    # --- Receber filtro do usuário
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # --- Buscar apenas agendamentos já realizados
    query = """
    SELECT sc.date_time, sv.price, p.name as professional_name
    FROM schedules sc
    JOIN services sv ON sc.service_id = sv.id
    JOIN professionals p ON sc.professional_id = p.id
    WHERE datetime(sc.date_time) <= ?
    """
    params = [now.strftime("%Y-%m-%d %H:%M:%S")]


    # Filtro por período, se houver
    if start_date:
        query += " AND date(s.date_time) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(s.date_time) <= ?"
        params.append(end_date)

    cur.execute(query, params)
    results = cur.fetchall()

    # --- Resumo geral
    total_services = len(results)
    total_price = sum([r['price'] for r in results])

    # --- Resumo por profissional
    summary_by_professional = {}
    for r in results:
        name = r['professional_name']
        if name not in summary_by_professional:
            summary_by_professional[name] = {'total_services': 0, 'total_price': 0.0}
        summary_by_professional[name]['total_services'] += 1
        summary_by_professional[name]['total_price'] += r['price']

    summary_by_professional = [
        {'name': k, 'total_services': v['total_services'], 'total_price': v['total_price']}
        for k, v in summary_by_professional.items()
    ]

    # --- Resumo diário
    daily_results = [r for r in results if datetime.strptime(r['date_time'], "%Y-%m-%d %H:%M:%S").date() == date.today()]
    daily_summary = {'total_services': len(daily_results), 'total_price': sum([r['price'] for r in daily_results])}

    # --- Resumo semanal (7 dias atrás)
    week_start = date.today() - timedelta(days=date.today().weekday())  # segunda-feira da semana
    weekly_results = [r for r in results if week_start <= datetime.strptime(r['date_time'], "%Y-%m-%d %H:%M:%S").date() <= date.today()]
    weekly_summary = {'total_services': len(weekly_results), 'total_price': sum([r['price'] for r in weekly_results])}

    # --- Resumo filtrado (se houver datas selecionadas)
    if results:
        filtered_summary = {'total_services': total_services, 'total_price': total_price}
        filtered_by_professional = summary_by_professional
    else:
        filtered_summary = None
        filtered_by_professional = []

    return render_template(
        "finance.html",
        total_summary={'total_services': total_services, 'total_price': total_price},
        summary_by_professional=summary_by_professional,
        daily_summary=daily_summary,
        weekly_summary=weekly_summary,
        filtered_summary=filtered_summary,
        filtered_by_professional=filtered_by_professional,
        start_date=start_date,
        end_date=end_date
    )
