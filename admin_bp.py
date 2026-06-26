# admin_bp.py

from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/users")
def admin_users():
    return render_template("admin_users.html")
