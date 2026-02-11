import mysql.connector
import os

# 1. Configuração (Lembrete: Mover para .env no futuro)
Config = {
    'user': 'ajudanoizapp_admin',
    'password': '@ss1st3nc14S3gvra!',
    'host': 'localhost',
}


def get_db_connection(incluir_banco=True):
    """Cria uma conexão com o MySQL de forma flexível."""
    parametros = Config.copy()
    if incluir_banco:
        parametros['database'] = 'ajudanoizapp_db'
    return mysql.connector.connect(**parametros)


# 2. Função para Criar Banco e Tabelas
def inicializar_banco():
    """Lê o schema.sql e prepara a estrutura do banco."""
    print("--- Inicializando Banco de Dados ---")
    # Conecta sem banco para garantir que pode criar o banco do zero
    conn = get_db_connection(incluir_banco=False)
    cursor = conn.cursor()

    try:
        # Busca o schema.sql no mesmo diretório deste arquivo
        caminho_sql = os.path.join(os.path.dirname(__file__), 'schema.sql')

        with open(caminho_sql, 'r', encoding='utf-8') as f:
            # Divide o arquivo por ';' para executar comando por comando
            comandos_sql = f.read().split(';')

        for comando in comandos_sql:
            if comando.strip():
                cursor.execute(comando)

        conn.commit()
        print("✅ Estrutura do banco verificada/criada.")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
    finally:
        cursor.close()
        conn.close()


# 3. Função de Autoteste de Integridade
def executar_autoteste():
    """Realiza um CRUD completo e faz rollback para validar o sistema."""
    print("--- Iniciando Autoteste de CRUD ---")
    conn = get_db_connection()  # Aqui já usa o banco ajudanoizapp_db
    cursor = conn.cursor()

    try:
        conn.start_transaction()

        # Teste de INSERT
        sql_ins = (
            "INSERT INTO usuarios (nome, email, senha_hash, cargo) "
            "VALUES (%s, %s, %s, %s)"
        )
        cursor.execute(sql_ins, ('Teste', 't@t.com', '123', 'admin'))
        id_teste = cursor.lastrowid
        print(f"   -> Insert OK (ID: {id_teste})")

        # Teste de SELECT
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (id_teste,))
        print(f"   -> Select OK ({cursor.fetchone()[0]})")

        # Teste de DELETE
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id_teste,))
        print("   -> Delete OK")

        print("✅ Autoteste finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Falha no Autoteste: {e}")
    finally:
        conn.rollback()  # Garante que o banco continue limpo
        cursor.close()
        conn.close()


# Bloco de execução direta (útil para testes isolados)
if __name__ == "__main__":
    inicializar_banco()
    executar_autoteste()
