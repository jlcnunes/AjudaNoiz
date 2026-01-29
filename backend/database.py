import mysql.connector

Config = {
    'user': 'ajudanoizapp_admin',
    'password': '@ss1st3nc14S3gvra!',
    'host': 'localhost',
    'database': 'ajudanoizapp_db'
}


def executar_autoteste():
    connection = mysql.connector.connect(**Config)
    cursor = connection.cursor()

    try:
        print("Iniciando autoteste...")
        # 1. Iniciar Transação
        # (impede que o AUTO_INCREMENT suba permanentemente)
        connection.start_transaction()

        # 2. CREATE (Insert de teste na tabela usuários)
        sql_insert = (
            "INSERT INTO usuarios (nome, email, senha_hash, cargo) "
            "VALUES (%s, %s, %s, %s)"
            )
        valores = ('Teste Sistema', 'teste@ajudanoiz.com', '123456', 'admin')
        cursor.execute(sql_insert, valores)
        # Pegamos o ID para usar nos próximos passos
        id_teste = cursor.lastrowid
        print(f"-> Passo 1: Usuário de teste inserido com ID {id_teste}")

        # 3. READ (Select para validar)
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (id_teste,))
        resultado = cursor.fetchone()
        print(f"-> Passo 2: Leitura confirmada para: {resultado[0]}")

        # 4. UPDATE (Alterar o nome)
        cursor.execute(
            "UPDATE usuarios SET nome = %s WHERE id = %s",
            ('Nome Alterado', id_teste))
        print("-> Passo 3: Atualização executada.")

        # 5. DELETE (Remover)
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id_teste,))
        print("-> Passo 4: Remoção executada.")

        print("✅ CRUD de teste finalizado com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante o autoteste: {e}")

    finally:
        # O PULO DO GATO: Rollback desfaz tudo, inclusive o salto do ID
        connection.rollback()
        cursor.close()
        connection.close()
        print("🧹 Limpeza concluída: O banco de dados permanece intacto.")


if __name__ == "__main__":
    executar_autoteste()
