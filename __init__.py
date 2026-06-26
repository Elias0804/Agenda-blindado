# init_auth.py
from db import init_auth_db

if __name__ == "__main__":
    init_auth_db()
    print("✅ Banco de autenticação (users.db) inicializado com sucesso!")
