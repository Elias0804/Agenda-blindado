from flask import Blueprint, request, render_template, redirect, url_for
from db import get_db

professionals_bp = Blueprint("professionals", __name__)

# -------------------------------
# Página de profissionais
# -------------------------------
@professionals_bp.route("/professionals", methods=["GET", "POST"])
def professionals():
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        specialty = request.form.get("specialty", None)

        cur.execute(
            "INSERT INTO professionals (name, phone, specialty) VALUES (?, ?, ?)",
            (name, phone, specialty),
        )
        db.commit()
        return redirect(url_for("professionals.professionals"))

    # carregar profissionais
    cur.execute("SELECT * FROM professionals")
    all_pros = cur.fetchall()

    return render_template("professionals.html", all_pros=all_pros)

# -------------------------------
# Editar professionals
# -------------------------------
@professionals_bp.route("/professionals/edit/<int:prof_id>", methods=["GET", "POST"])
def edit_professionals(prof_id):
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        specialty = request.form.get("specialty", None)
        cur.execute(
            "UPDATE professionals SET name=?, phone=?, specialty=? WHERE id=?",
            (name, phone, specialty, prof_id),
        )
        db.commit()
        return redirect(url_for("professionals.professionals"))

    cur.execute("SELECT * FROM professionals WHERE id=?", (prof_id,))
    prof = cur.fetchone()
    return render_template("edit_professionals.html", prof=prof)

# -------------------------------
# Excluir professionals
# -------------------------------
@professionals_bp.route("/professionals/delete/<int:prof_id>")
def delete_professionals(prof_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM professionals WHERE id=?", (prof_id,))
    db.commit()
    return redirect(url_for("professionals.professionals"))
