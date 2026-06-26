# migrate_to_user_dbs.py
import sqlite3
import os
from db import init_auth_db, ensure_user_db_dir, user_db_path, init_user_db

OLD_DB = "agenda.db"
AUTH_DB = "users.db"
COPY_GLOBAL_SERVICES_TO_ALL_USERS = False  # <-- ajuste: se True, copia services globais para cada usuário

def copy_users_from_old():
    old = sqlite3.connect(OLD_DB)
    old.row_factory = sqlite3.Row
    cur = old.cursor()

    # Criar auth_db e tabela (caso não exista)
    init_auth_db()
    auth = sqlite3.connect(AUTH_DB)
    auth.row_factory = sqlite3.Row

    # Se a tabela users existir no old DB, copie
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cur.fetchone():
            rows = cur.execute("SELECT id, name, email, password_hash FROM users").fetchall()
            a_cur = auth.cursor()
            for r in rows:
                # tenta inserir - se já existir por email, ignora
                try:
                    a_cur.execute("INSERT OR IGNORE INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                                  (r['id'], r['name'], r['email'], r['password_hash']))
                except Exception as e:
                    print("erro insert user:", e)
            auth.commit()
            print(f"Copiados {len(rows)} usuários para {AUTH_DB}")
        else:
            print("Tabela users não encontrada no DB antigo.")
    finally:
        old.close()
        auth.close()

def copy_per_user_tables():
    old = sqlite3.connect(OLD_DB)
    old.row_factory = sqlite3.Row
    try:
        # buscar lista de usuários no auth DB
        auth = sqlite3.connect(AUTH_DB)
        auth.row_factory = sqlite3.Row
        ucur = auth.cursor()
        urows = ucur.execute("SELECT id, email FROM users").fetchall()
        user_ids = [r['id'] for r in urows]
        print("Usuários encontrados:", user_ids)
        ensure_user_db_dir()

        # Copiar clients usando coluna user_id do old DB (se existir)
        old_cur = old.cursor()
        old_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
        if old_cur.fetchone():
            clients = old.execute("SELECT * FROM clients").fetchall()
            for c in clients:
                uid = c['user_id'] if 'user_id' in c.keys() else None
                if uid:
                    path = user_db_path(uid)
                    conn = sqlite3.connect(path)
                    conn.row_factory = sqlite3.Row
                    init_user_db(conn)
                    conn.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", (c['name'], c.get('phone')))
                    conn.commit()
                    conn.close()
            print("Clientes migrados (usando campo user_id).")
        else:
            print("Tabela clients não existe no DB antigo.")

        # Copiar services: se existirem serviços e tiverem user_id, copia por usuário.
        old_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
        if old_cur.fetchone():
            # checar se services tem coluna user_id
            cols = [c[1] for c in old.execute("PRAGMA table_info(services)")]
            services = old.execute("SELECT * FROM services").fetchall()
            if 'user_id' in cols:
                for s in services:
                    uid = s['user_id']
                    path = user_db_path(uid)
                    conn = sqlite3.connect(path)
                    conn.row_factory = sqlite3.Row
                    init_user_db(conn)
                    conn.execute("INSERT INTO services (name, category, price, duration, promotion) VALUES (?, ?, ?, ?, ?)",
                                 (s['name'], s['category'], s['price'], s['duration'], s.get('promotion', 0)))
                    conn.commit()
                    conn.close()
                print("Services migrados por user_id.")
            else:
                if COPY_GLOBAL_SERVICES_TO_ALL_USERS:
                    for uid in user_ids:
                        path = user_db_path(uid)
                        conn = sqlite3.connect(path)
                        conn.row_factory = sqlite3.Row
                        init_user_db(conn)
                        for s in services:
                            conn.execute("INSERT INTO services (name, category, price, duration, promotion) VALUES (?, ?, ?, ?, ?)",
                                         (s['name'], s['category'], s['price'], s['duration'], s.get('promotion', 0)))
                        conn.commit()
                        conn.close()
                    print("Services globais copiados para todos os usuários.")
                else:
                    print("Services são globais (sem user_id). Não foram copiados. Ajuste COPY_GLOBAL_SERVICES_TO_ALL_USERS se desejar.")
        else:
            print("Tabela services não existe no DB antigo.")
    finally:
        old.close()

if __name__ == "__main__":
    print("1) Copiando usuários para users.db ...")
    copy_users_from_old()
    print("2) Migrando clients/services para DBs por usuário ...")
    copy_per_user_tables()
    print("Migração concluída. Verifique user_dbs/ e users.db")
