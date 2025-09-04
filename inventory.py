from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
from db import get_db  # sua função de acesso ao DB
import sqlite3

inventory_bp = Blueprint("inventory", __name__, template_folder="templates")

DB_FILE = "agenda.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Listagem do estoque
@inventory_bp.route('/')
def inventory():
    db = get_db()
    items = db.execute("SELECT * FROM inventory").fetchall()
    return render_template("inventory.html", items=items)

# Adicionar item manualmente
@inventory_bp.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        db = get_db()
        db.execute("INSERT INTO inventory (name, category, quantity, unit_price) VALUES (?, ?, ?, ?)",
                   (name, category, quantity, unit_price))
        db.commit()
        flash("Produto adicionado!", "success")
        return redirect(url_for('inventory.inventory'))
    return render_template("add_item.html")

# Editar item
inventory_bp = Blueprint("inventory", __name__, template_folder="templates")

DB_FILE = "agenda.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@inventory_bp.route("/inventory/add", methods=["GET", "POST"])
def add_item():
    conn = get_db()

    if request.method == "POST":
        try:
            name = request.form["name"]
            category = request.form["category"]
            quantity = int(request.form["quantity"])
            price = float(request.form["price"])  # CORRETO

            conn.execute(
                "INSERT INTO inventory (name, category, quantity, price) VALUES (?, ?, ?, ?)",
                (name, category, quantity, price)
            )
            conn.commit()
            flash("Item adicionado com sucesso!", "success")
            return redirect(url_for("inventory.add_item"))

        except KeyError as e:
            flash(f"Campo ausente no formulário: {e}", "error")
        except ValueError:
            flash("Erro: insira valores válidos para quantidade e preço.", "error")

    cursor = conn.execute("SELECT * FROM inventory")
    items = cursor.fetchall()
    conn.close()
    return render_template("add_item.html", items=items)

# Excluir item
@inventory_bp.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    db = get_db()
    db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    db.commit()
    flash("Produto excluído!", "success")
    return redirect(url_for('inventory.inventory'))

# Upload de Excel/CSV
@inventory_bp.route('/upload', methods=['POST'])
def upload_excel():
    if 'excel_file' not in request.files:
        flash("Nenhum arquivo selecionado!", "error")
        return redirect(url_for('inventory.inventory'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash("Nenhum arquivo selecionado!", "error")
        return redirect(url_for('inventory.inventory'))

    try:
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)

        db = get_db()
        for _, row in df.iterrows():
            db.execute("""
                INSERT INTO inventory (name, category, quantity, unit_price)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                category=excluded.category,
                quantity=excluded.quantity,
                unit_price=excluded.unit_price
            """, (row['Produto'], row['Categoria'], row['Quantidade'], row['Preço Unitário']))
        db.commit()
        flash("Planilha importada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao processar planilha: {str(e)}", "error")
    
    return redirect(url_for('inventory.inventory'))
def init_db():
    conn = get_db()
    # Cria a tabela se não existir
    conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL
    )
    """)
    # Adiciona a coluna price se ainda não existir
    try:
        conn.execute("ALTER TABLE inventory ADD COLUMN price REAL DEFAULT 0")
    except sqlite3.OperationalError:
        # Coluna já existe
        pass
    conn.commit()
    conn.close()
