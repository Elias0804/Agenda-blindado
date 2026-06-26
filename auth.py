import os
from flask import Blueprint, request, redirect, url_for, session, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from yourdatabase import db, User  # ajuste conforme seu modelo

auth = Blueprint("auth", __name__)
oauth = OAuth()

# ------------------------------------------------------------
#  Inicializar OAuth (chamado dentro do app.py)
# ------------------------------------------------------------
def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ------------------------------------------------------------
#  LOGIN
# ------------------------------------------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]  # pode ser email ou cpf
        password = request.form["password"]

        user = User.query.filter(
            (User.email == username) | (User.cpf == username)
        ).first()

        if not user:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("auth.login"))

        if not user.password or not check_password_hash(user.password, password):
            flash("Senha incorreta.", "error")
            return redirect(url_for("auth.login"))

        # salva sessão
        session["user_id"] = user.id
        flash(f"Bem-vindo, {user.name}!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


# ------------------------------------------------------------
#  LOGIN COM GOOGLE
# ------------------------------------------------------------
@auth.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth.route("/login/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get(
        "https://openidconnect.googleapis.com/v1/userinfo"
    ).json()

    if not user_info:
        flash("Erro ao autenticar com Google", "error")
        return redirect(url_for("auth.login"))

    email = user_info.get("email")
    name = user_info.get("name", "Usuário Google")

    # verifica se usuário existe
    user = User.query.filter_by(email=email).first()

    # cria se não existir
    if not user:
        user = User(
            name=name,
            email=email,
            password=None,  # login por Google não usa senha
            role="funcionario",
            type="colaborador",
        )
        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.id
    flash(f"Bem-vindo, {name}!", "success")
    return redirect(url_for("dashboard.index"))


# ------------------------------------------------------------
#  CADASTRO
# ------------------------------------------------------------
@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # dados enviados pelo form
        user = User(
            name=request.form["name"],
            cpf=request.form["cpf"],
            phone=request.form["phone"],
            role=request.form["role"],
            type=request.form["type"],
            commission=request.form["commission"],
            cnpj=request.form["cnpj"],
            razao=request.form["razao"],
            inscricao=request.form["inscricao"],
            endereco=request.form["endereco"],
            email_nf=request.form["email_nf"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"]),
        )

        db.session.add(user)
        db.session.commit()

        flash("Conta criada com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ------------------------------------------------------------
#  LOGOUT
# ------------------------------------------------------------
@auth.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))
