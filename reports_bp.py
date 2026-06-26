# reports_bp.py

from flask import Blueprint, render_template

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

@reports_bp.route("/")
def index():
    return render_template("reports.html")  # Você pode criar esse HTML depois
