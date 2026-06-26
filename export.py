from flask import Blueprint, redirect, url_for, session, send_file, flash
from db import get_db
from datetime import datetime
import io

export_bp = Blueprint('export', __name__, url_prefix='/export')

@export_bp.route('/')
def export_excel():
    if not session.get('user'):
        return redirect(url_for('auth.login'))

    conn = get_db()
    try:
        import pandas as pd
        clients_df = pd.read_sql_query('SELECT * FROM clients', conn)
        schedules_df = pd.read_sql_query('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                                           FROM schedules s
                                           LEFT JOIN clients c ON c.id = s.client_id
                                           LEFT JOIN services sv ON sv.id = s.service_id''', conn)
        if 'date_time' in schedules_df.columns:
            schedules_df['date_time'] = schedules_df['date_time'].apply(lambda x: x.replace('T',' ') if isinstance(x, str) else x)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            clients_df.to_excel(writer, index=False, sheet_name='Clientes')
            schedules_df.to_excel(writer, index=False, sheet_name='Agendamentos')
        output.seek(0)
        filename = f'planilha_agenda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(output, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception:
        # Fallback CSV + ZIP
        import csv
        import zipfile
        cur = conn.cursor()
        cur.execute('SELECT * FROM clients')
        clients_rows = cur.fetchall()
        clients_cols = [desc[0] for desc in cur.description]

        cur.execute('''SELECT s.id, c.name as client_name, s.date_time, sv.name as service_name, sv.price, sv.cost, s.notes
                       FROM schedules s
                       LEFT JOIN clients c ON c.id = s.client_id
                       LEFT JOIN services sv ON sv.id = s.service_id''')
        sched_rows = cur.fetchall()
        sched_cols = [desc[0] for desc in cur.description]

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            clients_io = io.StringIO()
            writer = csv.writer(clients_io)
            writer.writerow(clients_cols)
            for r in clients_rows:
                writer.writerow([r[col] for col in clients_cols])
            zf.writestr('clientes.csv', clients_io.getvalue())

            sched_io = io.StringIO()
            writer = csv.writer(sched_io)
            writer.writerow(sched_cols)
            for r in sched_rows:
                row = []
                for col in sched_cols:
                    val = r[col]
                    if col == 'date_time' and isinstance(val, str):
                        val = val.replace('T', ' ')
                    row.append(val)
                writer.writerow(row)
            zf.writestr('agendamentos.csv', sched_io.getvalue())

        zip_buffer.seek(0)
        filename = f'planilha_agenda_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        return send_file(zip_buffer, download_name=filename, as_attachment=True, mimetype='application/zip')
    finally:
        conn.close()
