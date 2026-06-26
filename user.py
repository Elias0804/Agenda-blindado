from yourdatabase import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Dados pessoais
    name = db.Column(db.String(120))
    cpf = db.Column(db.String(20), unique=True)
    phone = db.Column(db.String(30))

    # Trabalho
    role = db.Column(db.String(50))
    type = db.Column(db.String(20))  # cooperado / funcionário
    commission = db.Column(db.Float)

    # Nota Fiscal
    cnpj = db.Column(db.String(20))
    razao = db.Column(db.String(120))
    inscricao = db.Column(db.String(30))
    endereco = db.Column(db.String(200))
    email_nf = db.Column(db.String(120))

    # Acesso
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
