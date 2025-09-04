import os
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
import mercadopago
from db import get_db, init_db
from datetime import datetime, timedelta
from inventory import inventory_bp
import sqlite3



# -------------------- CARREGAR VARIÁVEIS DE AMBIENTE --------------------
load_dotenv()

# -------------------- INICIALIZAÇÃO DO APP --------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "troque_esta_chave_por_uma_secreta")

# -------------------- IMPORTAR BLUEPRINTS --------------------
from auth import auth_bp
from clients import clients_bp
from schedules import schedules_bp
from services_bp import services_bp
from export import export_bp
from finance import finance_bp
from flask import Flask
from professionals import professionals_bp
from inventory import inventory_bp

DB_FILE = "agenda.db"
''
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Cria tabela se não existir
def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        duration INTEGER NOT NULL,
        promotion INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

init_db()

# Rota principal de serviços
@app.route("/services", methods=["GET", "POST"])
def services():
    conn = get_db()

    if request.method == "POST":
        if "add" in request.form:
            name = request.form["name"]
            category = request.form["category"]
            price = float(request.form["price"])
            duration = int(request.form["duration"])
            conn.execute(
                "INSERT INTO services (name, category, price, duration) VALUES (?, ?, ?, ?)",
                (name, category, price, duration)
            )
            conn.commit()

        elif "update" in request.form:
            service_id = int(request.form["service_id"])
            name = request.form["name"]
            category = request.form["category"]
            price = float(request.form["price"])
            duration = int(request.form["duration"])
            promotion = 1 if request.form.get("promotion") else 0
            conn.execute(
                "UPDATE services SET name=?, category=?, price=?, duration=?, promotion=? WHERE id=?",
                (name, category, price, duration, promotion, service_id)
            )
            conn.commit()

        elif "delete" in request.form:
            service_id = int(request.form["service_id"])
            conn.execute("DELETE FROM services WHERE id=?", (service_id,))
            conn.commit()

        elif "clear_all" in request.form:
            conn.execute("DELETE FROM services")
            conn.commit()

        return redirect(url_for("services"))

    cursor = conn.execute("SELECT * FROM services")
    services_list = cursor.fetchall()
    conn.close()
    return render_template("services.html", services=services_list)


# -------------------- REGISTRAR BLUEPRINTS --------------------
app.register_blueprint(auth_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(schedules_bp)
app.register_blueprint(services_bp)
app.register_blueprint(export_bp)
app.register_blueprint(finance_bp, url_prefix="/finance")  # define prefixo correto
app.register_blueprint(inventory_bp)
app.register_blueprint(professionals_bp)


# -------------------- INICIALIZAÇÃO DO BANCO DE DADOS --------------------
with app.app_context():
    init_db()

# -------------------- CONFIGURAÇÃO MERCADO PAGO --------------------
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN", ""))

# -------------------- ROTAS PRINCIPAIS --------------------
@app.route("/")
def index():
    return render_template("register.html")


@app.route("/pagar", methods=["POST"])
def pagar():
    form = request.form
    plano = form.get("plano")
    email = form.get("email")

    preco_base = 0
    descricao = ""
    valor_final = 0

    if plano == "basico":
        preco_base = 29.90
        descricao = "Plano Básico"
        valor_final = preco_base
    elif plano == "professionals":
        preco_base = 59.90
        descricao = "Plano professionals"
        valor_final = preco_base
    elif plano == "premium":
        preco_base = 99.90
        descricao = "Plano Premium"
        valor_final = preco_base
    elif plano == "avista":
        preco_base = 120.00
        desconto = 0.10
        valor_final = preco_base * (1 - desconto)
        descricao = "Plano Avista - 10% desconto"
    elif plano == "parcelado":
        preco_base = 120.00
        juros = 0.05
        valor_final = preco_base * (1 + juros)
        descricao = "Plano Parcelado - 5% juros"
    else:
        flash("Plano inválido")
        return redirect(url_for("index"))

    pagamento = {
        "transaction_amount": round(valor_final, 2),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": email}
    }

    try:
        resultado = sdk.payment().create(pagamento)
        link_pagamento = resultado["response"]["point_of_interaction"]["transaction_data"]["ticket_url"]
        return redirect(link_pagamento)
    except Exception as e:
        flash(f"Erro ao criar pagamento: {e}")
        return redirect(url_for("index"))

# -------------------- WEBHOOK MERCADO PAGO --------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    print("Notificação recebida:", request.json)
    return jsonify({"status": "ok"})

# -------------------- EXECUÇÃO DO APP --------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)


def create_app():
    app = Flask(__name__)
    app.secret_key = "sua_chave_segura"

    app.register_blueprint(clients_bp)
    app.register_blueprint(professionals_bp)

    return app