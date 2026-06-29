from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
from db import get_user_db

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

# uses centralized `get_user_db` from `db.py`

# ==================== Listar produtos ====================
@inventory_bp.route("/", methods=["GET"])
def inventory():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    rows = conn.execute("SELECT * FROM inventory ORDER BY id").fetchall()
    items = [dict(row) for row in rows]

    for i, item in enumerate(items):
        total_used = conn.execute(
            "SELECT COALESCE(SUM(quantity_used),0) as total FROM schedule_products WHERE product_id=?",
            (item["id"],)
        ).fetchone()["total"]
        item["total_used"] = total_used
        if item.get("usage_per_service", 0) > 0:
            item["usage_per_service_clients"] = int(item["quantity"] // item["usage_per_service"])
        else:
            item["usage_per_service_clients"] = 0

    conn.close()
    return render_template("inventory.html", items=items)

# ==================== Adicionar produto ====================
@inventory_bp.route("/add", methods=["GET", "POST"])
def add_item():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form["name"]
        category = request.form.get("category", "")
        quantity = float(request.form.get("quantity") or 0)
        unit_price = float(request.form.get("unit_price") or 0)
        usage_per_service = float(request.form.get("usage_per_service") or 0)
        min_stock = int(request.form.get("min_stock") or 0)

        conn = get_user_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO inventory (name, category, quantity, unit_price, usage_per_service, min_stock)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, quantity, unit_price, usage_per_service, min_stock)
        )
        conn.commit()
        conn.close()
        flash("Produto adicionado.", "success")
        return redirect(url_for("inventory.inventory"))

    return render_template("inventory_add.html")

# ==================== Editar produto ====================
@inventory_bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    if request.method == "POST":
        name = request.form["name"]
        category = request.form.get("category", "")
        quantity = float(request.form.get("quantity") or 0)
        unit_price = float(request.form.get("unit_price") or 0)
        usage_per_service = float(request.form.get("usage_per_service") or 0)
        min_stock = int(request.form.get("min_stock") or 0)

        conn.execute(
            """
            UPDATE inventory
            SET name=?, category=?, quantity=?, unit_price=?, usage_per_service=?, min_stock=?
            WHERE id=?
            """,
            (name, category, quantity, unit_price, usage_per_service, min_stock, item_id)
        )
        conn.commit()
        conn.close()
        flash("Produto atualizado.", "success")
        return redirect(url_for("inventory.inventory"))

    item = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
    conn.close()
    if not item:
        flash("Item não encontrado.", "error")
        return redirect(url_for("inventory.inventory"))
    return render_template("inventory_edit.html", item=dict(item))

# ==================== Deletar produto ====================
@inventory_bp.route("/delete/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    conn = get_user_db()
    conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Produto excluído.", "success")
    return redirect(url_for("inventory.inventory"))

# ==================== Upload Excel ====================
@inventory_bp.route("/upload_excel", methods=["POST"])
def upload_excel():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    file = request.files.get("file")
    if not file:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("inventory.inventory"))

    import pandas as pd
    try:
        df = pd.read_excel(file)
        conn = get_user_db()
        cur = conn.cursor()
        for _, row in df.iterrows():
            cur.execute(
                "INSERT INTO inventory (name, category, quantity, unit_price, usage_per_service, min_stock) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    row.get("name", ""),
                    row.get("category", ""),
                    row.get("quantity", 0),
                    row.get("unit_price", 0),
                    row.get("usage_per_service", 0),
                    row.get("min_stock", 0),
                )
            )
        conn.commit()
        conn.close()
        flash("Produtos importados com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao processar o arquivo: {e}", "error")

    return redirect(url_for("inventory.inventory"))
