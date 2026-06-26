# services_db.py (melhorado com banco separado por usuário)

from flask import Blueprint, request, redirect, url_for, session, render_template, flash
import pandas as pd
import os
import sqlite3
from werkzeug.utils import secure_filename

services_bp = Blueprint('services', __name__, url_prefix='/services')

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv", "xlsx"}

# ------------------ FUNÇÕES AUXILIARES ------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_db():
    """Retorna a conexão com o banco do usuário logado"""
    user_id = session.get("user_id")
    if not user_id:
        raise RuntimeError("Usuário não autenticado")

    db_path = f"agenda_{user_id}.db"
    init_needed = not os.path.exists(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if init_needed:
        init_user_db(conn)

    return conn

def init_user_db(conn):
    """Cria tabelas no banco do usuário, se não existirem"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            duration INTEGER DEFAULT 0,
            avg_quantity REAL DEFAULT 0,
            promotion INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity_used REAL DEFAULT 0,
            FOREIGN KEY(service_id) REFERENCES services(id),
            FOREIGN KEY(product_id) REFERENCES inventory(id)
        )
    """)

    conn.commit()

# ------------------ ROTAS ------------------

@services_bp.route('/', methods=['GET','POST'])
def services():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    cur = conn.cursor()

    # detectar colunas nas tabelas
    svc_cols = [r['name'] for r in cur.execute("PRAGMA table_info(services)").fetchall()]
    sp_cols = [r['name'] for r in cur.execute("PRAGMA table_info(service_products)").fetchall()]

    sp_quantity_col = 'quantity_used' if 'quantity_used' in sp_cols else (
        'avg_quantity' if 'avg_quantity' in sp_cols else None
    )

    # ---------- POST ----------
    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form.get('name', '').strip()
            price = float(request.form.get('price') or 0)
            duration = int(request.form.get('duration') or 0)
            avg_quantity = request.form.get('avg_quantity')
            avg_quantity = float(avg_quantity) if avg_quantity not in (None, '') else None
            promotion = int(request.form.get('promotion') or 0) if 'promotion' in svc_cols else None

            fields, values = ['name'], [name]
            if 'price' in svc_cols: fields.append('price'); values.append(price)
            if 'duration' in svc_cols: fields.append('duration'); values.append(duration)
            if 'avg_quantity' in svc_cols: fields.append('avg_quantity'); values.append(avg_quantity or 0)
            if 'promotion' in svc_cols: fields.append('promotion'); values.append(promotion or 0)

            sql = f"INSERT INTO services ({','.join(fields)}) VALUES ({','.join(['?']*len(fields))})"
            cur.execute(sql, tuple(values))
            service_id = cur.lastrowid

            # produtos vinculados
            products_ids = request.form.getlist('products_ids')
            for pid in products_ids:
                try:
                    pid_int = int(pid)
                except ValueError:
                    continue
                qty_val = request.form.get(f'products_qty_{pid}', None)
                if sp_quantity_col:
                    qty_num = float(qty_val) if qty_val not in (None, '') else 0
                    cur.execute(
                        f'INSERT INTO service_products (service_id, product_id, {sp_quantity_col}) VALUES (?,?,?)',
                        (service_id, pid_int, qty_num)
                    )
                else:
                    cur.execute('INSERT INTO service_products (service_id, product_id) VALUES (?,?)',
                                (service_id, pid_int))

            conn.commit()
            flash('Serviço adicionado com sucesso!', 'success')
            conn.close()
            return redirect(url_for('services.services'))

        # UPDATE
        if 'update' in request.form:
            sid = int(request.form.get('service_id'))
            name = request.form.get('name', '').strip()
            price = float(request.form.get('price') or 0)
            duration = int(request.form.get('duration') or 0)
            avg_quantity = request.form.get('avg_quantity')
            avg_quantity = float(avg_quantity) if avg_quantity not in (None, '') else None
            promotion = int(request.form.get('promotion') or 0) if 'promotion' in svc_cols else None

            set_parts, params = [], []
            if 'name' in svc_cols: set_parts.append('name=?'); params.append(name)
            if 'price' in svc_cols: set_parts.append('price=?'); params.append(price)
            if 'duration' in svc_cols: set_parts.append('duration=?'); params.append(duration)
            if 'avg_quantity' in svc_cols: set_parts.append('avg_quantity=?'); params.append(avg_quantity or 0)
            if 'promotion' in svc_cols: set_parts.append('promotion=?'); params.append(promotion or 0)

            if set_parts:
                sql = f"UPDATE services SET {', '.join(set_parts)} WHERE id=?"
                params.append(sid)
                cur.execute(sql, tuple(params))

            cur.execute('DELETE FROM service_products WHERE service_id=?', (sid,))
            for pid in request.form.getlist('products_ids'):
                try:
                    pid_int = int(pid)
                except ValueError:
                    continue
                qty_val = request.form.get(f'products_qty_{pid}', None)
                if sp_quantity_col:
                    qty_num = float(qty_val) if qty_val not in (None, '') else 0
                    cur.execute(
                        f'INSERT INTO service_products (service_id, product_id, {sp_quantity_col}) VALUES (?,?,?)',
                        (sid, pid_int, qty_num)
                    )
                else:
                    cur.execute('INSERT INTO service_products (service_id, product_id) VALUES (?,?)',
                                (sid, pid_int))

            conn.commit()
            flash('Serviço atualizado com sucesso!', 'info')
            conn.close()
            return redirect(url_for('services.services'))

        # DELETE
        if 'delete' in request.form:
            sid = int(request.form.get('service_id'))
            cur.execute('DELETE FROM service_products WHERE service_id=?', (sid,))
            cur.execute('DELETE FROM services WHERE id=?', (sid,))
            conn.commit()
            flash('Serviço excluído!', 'success')
            conn.close()
            return redirect(url_for('services.services'))

        # CLEAR ALL
        if 'clear_all' in request.form:
            cur.execute('DELETE FROM service_products')
            cur.execute('DELETE FROM services')
            conn.commit()
            flash('Todos os serviços foram excluídos!', 'warning')
            conn.close()
            return redirect(url_for('services.services'))

    # ---------- GET ----------
    cur.execute('SELECT * FROM services ORDER BY id')
    services_data = [dict(r) for r in cur.fetchall()]

    service_products, service_products_ids = {}, {}
    for s in services_data:
        if sp_quantity_col:
            sql = f'''
                SELECT sp.product_id, i.name, sp.{sp_quantity_col} as quantity
                FROM service_products sp
                JOIN inventory i ON i.id = sp.product_id
                WHERE sp.service_id=? ORDER BY i.id
            '''
            rows_sp = cur.execute(sql, (s['id'],)).fetchall()
            service_products[s['id']] = [{"id": r["product_id"], "name": r["name"], "quantity": r["quantity"]} for r in rows_sp]
            service_products_ids[s['id']] = [r["product_id"] for r in rows_sp]
        else:
            sql = '''
                SELECT sp.product_id, i.name
                FROM service_products sp
                JOIN inventory i ON i.id = sp.product_id
                WHERE sp.service_id=? ORDER BY i.id
            '''
            rows_sp = cur.execute(sql, (s['id'],)).fetchall()
            service_products[s['id']] = [{"id": r["product_id"], "name": r["name"], "quantity": None} for r in rows_sp]
            service_products_ids[s['id']] = [r["product_id"] for r in rows_sp]

    cur.execute('SELECT id, name, quantity FROM inventory WHERE category="uso" ORDER BY id')
    inventory_items = [dict(r) for r in cur.fetchall()]

    conn.close()
    return render_template(
        'services.html',
        services=services_data,
        inventory_items=inventory_items,
        service_products=service_products,
        service_products_ids=service_products_ids
    )
