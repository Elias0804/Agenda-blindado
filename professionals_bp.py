from flask import Blueprint, request, render_template, redirect, url_for, send_file, session, flash
from db import get_user_db
import io
from reportlab.pdfgen import canvas
from datetime import date
import os

professionals_bp = Blueprint("professionals", __name__, url_prefix='/professionals')

# Pasta para salvar PDFs
UPLOAD_FOLDER = "static/nfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Página de profissionais + cadastro
# -------------------------------
@professionals_bp.route("/", methods=["GET", "POST"])
def professionals():
    conn = get_user_db()
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form.get("phone", "")
        specialty = request.form.get("specialty", "")
        cpf = request.form.get("cpf", "")

        cur.execute(
            "INSERT INTO professionals (name, phone, specialty, cpf) VALUES (?, ?, ?, ?)",
            (name, phone, specialty, cpf),
        )
        conn.commit()
        flash("Profissional cadastrado com sucesso!", "success")
        return redirect(url_for("professionals.professionals"))

    # Carregar profissionais
    cur.execute("SELECT * FROM professionals")
    all_pros = cur.fetchall()

    conn.close()
    return render_template("professionals.html", all_pros=all_pros)


# -------------------------------
# Editar profissional
# -------------------------------
@professionals_bp.route("/edit/<int:prof_id>", methods=["GET", "POST"])
def edit_professionals(prof_id):
    conn = get_user_db()
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form.get("phone", "")
        specialty = request.form.get("specialty", "")
        cpf = request.form.get("cpf", "")

        cur.execute(
            "UPDATE professionals SET name=?, phone=?, specialty=?, cpf=? WHERE id=?",
            (name, phone, specialty, cpf, prof_id),
        )
        conn.commit()
        conn.close()
        flash("Profissional atualizado com sucesso!", "success")
        return redirect(url_for("professionals.professionals"))

    cur.execute("SELECT * FROM professionals WHERE id=?", (prof_id,))
    prof = cur.fetchone()
    conn.close()
    return render_template("edit_professionals.html", prof=prof)


# -------------------------------
# Excluir profissional
# -------------------------------
@professionals_bp.route("/delete/<int:prof_id>")
def delete_professionals(prof_id):
    conn = get_user_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM professionals WHERE id=?", (prof_id,))
    conn.commit()
    conn.close()
    flash("Profissional excluído com sucesso!", "success")
    return redirect(url_for("professionals.professionals"))


# -------------------------------
# Emitir Nota Fiscal (PDF)
# -------------------------------
@professionals_bp.route("/<int:prof_id>/emitir_nf", methods=["GET", "POST"])
def emitir_nf(prof_id):
    conn = get_user_db()
    conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    cur = conn.cursor()

    cur.execute("SELECT * FROM professionals WHERE id = ?", (prof_id,))
    prof = cur.fetchone()
    if not prof:
        conn.close()
        flash("Profissional não encontrado.", "error")
        return redirect(url_for("professionals.professionals"))

    if request.method == "POST":
        numero = request.form["numero"]
        valor = request.form["valor"]
        data_emissao = request.form.get("data_emissao", str(date.today()))
        user_id = session.get("user_id")
        dono_nome = session.get("user", {}).get("nome", "Usuário")

        # Gerar PDF
        filename = f"NF_{numero}_{prof['name'].replace(' ', '_')}.pdf"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        pdf = canvas.Canvas(filepath)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, 800, f"Nota Fiscal - Número: {numero}")
        pdf.drawString(50, 780, f"Emitido por: {dono_nome}")
        pdf.drawString(50, 760, f"Profissional: {prof['name']}")
        pdf.drawString(50, 740, f"CPF: {prof['cpf']} | CNPJ: {prof['cnpj']}")
        pdf.drawString(50, 720, f"Especialidade: {prof['specialty']}")
        pdf.drawString(50, 700, f"Data de Emissão: {data_emissao}")
        pdf.drawString(50, 680, f"Valor: R$ {valor}")
        pdf.save()

        # Salvar no banco
        cur.execute(
            "INSERT INTO notas_fiscais (numero, profissional_id, dono_id, data_emissao, valor, arquivo_pdf) VALUES (?, ?, ?, ?, ?, ?)",
            (numero, prof_id, user_id, data_emissao, valor, f"nfs/{filename}")
        )
        conn.commit()
        conn.close()

        flash("Nota Fiscal emitida com sucesso!", "success")
        return redirect(url_for("professionals.professionals"))

    conn.close()
    return render_template("emitir_nf.html", prof=prof, today=str(date.today()))
