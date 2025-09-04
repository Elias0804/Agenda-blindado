from flask import Blueprint, request, render_template, redirect, url_for
from db import get_db

clients_bp = Blueprint("clients", __name__)

# -------------------------------
# Página de clientes
# -------------------------------
@clients_bp.route("/clients", methods=["GET", "POST"])
def clients():
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        notes = request.form.get("notes", None)

        cur.execute(
            "INSERT INTO clients (name, phone, notes) VALUES (?, ?, ?)",
            (name, phone, notes),
        )
        db.commit()
        return redirect(url_for("clients.clients"))

    # carregar clientes
    cur.execute("SELECT * FROM clients")
    all_clients = cur.fetchall()

    return render_template("clients.html", all_clients=all_clients)

# -------------------------------
# Editar cliente
# -------------------------------
@clients_bp.route("/clients/edit/<int:client_id>", methods=["GET", "POST"])
def edit_client(client_id):
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        notes = request.form.get("notes", None)
        cur.execute(
            "UPDATE clients SET name=?, phone=?, notes=? WHERE id=?",
            (name, phone, notes, client_id),
        )
        db.commit()
        return redirect(url_for("clients.clients"))

    cur.execute("SELECT * FROM clients WHERE id=?", (client_id,))
    client = cur.fetchone()
    return render_template("edit_client.html", client=client)

# -------------------------------
# Excluir cliente
# -------------------------------
@clients_bp.route("/clients/delete/<int:client_id>")
def delete_client(client_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM clients WHERE id=?", (client_id,))
    db.commit()
    return redirect(url_for("clients.clients"))
