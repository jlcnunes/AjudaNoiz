from werkzeug.security import generate_password_hash
from database import get_db_connection
import os


def cadastrar_primeiro_admin():
    nome = os.environ["ADMIN_NAME"]
    email = os.environ["ADMIN_USER"]
    senha_plana = os.environ["ADMIN_PASSWORD"]

    # * Gerando o Hash
    hash_seguro = generate_password_hash(senha_plana)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql = (
            "INSERT INTO usuarios (nome, email, senha_hash, cargo) "
            "VALUES (%s, %s, %s, %s)"
        )
        cursor.execute(sql, (nome, email, hash_seguro, 'admin'))
        conn.commit()
        print(f"✅ Usuário {nome} criado com sucesso!")
        print(f"🔐 Hash gerado: {hash_seguro[:20]}...")
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    cadastrar_primeiro_admin()
