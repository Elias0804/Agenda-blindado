import os
from flask import Flask, request, render_template, redirect, url_for, jsonify
from dotenv import load_dotenv
import mercadopago
from db import init_db
from auth import auth_bp
from clients import clients_bp
from schedules import schedules_bp
from services import services_bp
from export import export_bp


load_dotenv()

app = Flask(__name__)
app.secret_key = "troque_esta_chave_por_uma_secreta"

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(schedules_bp)
app.register_blueprint(services_bp)
app.register_blueprint(export_bp)

# Inicializa banco ao rodar o app
with app.app_context():
    init_db()

# Configura MercadoPago SDK
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

# Página inicial de cadastro e escolha do plano
@app.route("/")
def index():
    return render_template("cadastro.html")

# Rota para criar pagamento
@app.route("/pagar", methods=["POST"])
def pagar():
    print("Dados recebidos:", request.form)  # Aqui dentro da função, onde request está disponível
    plano = request.form.get('plano')
    plano = request.form.get("plano")
    email = request.form.get("email")

    plano = request.form.get('plano')
    if plano == "basico":
        preco_base = 29.90
        descricao = "Plano Básico"
    elif plano == "profissional":
        preco_base = 59.90
        descricao = "Plano Profissional"
    elif plano == "premium":
        preco_base = 99.90
        descricao = "Plano Premium"
    elif plano == "avista":
        preco_base = 120.00
        desconto = 0.10
        preco_final = preco_base * (1 - desconto)
        descricao = "Plano Avista - 10% desconto"
    elif plano == "parcelado":
        preco_base = 120.00
        juros = 0.05
        preco_final = preco_base * (1 + juros)
        descricao = "Plano Parcelado - 5% juros"
    else:
        return "Plano inválido", 400

    # A partir daqui, defina o valor que vai para o pagamento:
    if plano in ["basico", "profissional", "premium"]:
        valor_final = preco_base
    elif plano == "avista":
        valor_final = preco_final
    elif plano == "parcelado":
        valor_final = preco_final



    pagamento = {
        "transaction_amount": valor_final,
        "description": descricao,
        "payment_method_id": "pix",  # pode trocar para cartão se quiser
        "payer": {"email": email}
    }

    resultado = sdk.payment().create(pagamento)
    link_pagamento = resultado["response"]["point_of_interaction"]["transaction_data"]["ticket_url"]

    return redirect(link_pagamento)

# Webhook para receber confirmações de pagamento
@app.route("/webhook", methods=["POST"])
def webhook():
    print("Notificação recebida:", request.json)
    # Atualize status do pagamento no banco aqui se precisar
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
