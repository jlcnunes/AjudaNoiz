from flask import Flask, render_template, request, redirect
from database import inicializar_banco, executar_autoteste, get_db_connection

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/enviar', methods=['POST'])
def enviar():
    # * 1. Capturar os dados do formulário
    nome = request.form.get('nome')
    email = request.form.get('email')
    whatsapp = request.form.get('whatsapp')
    servico = request.form.get('servico')
    descricao = request.form.get('descricao')

    # * 2. Salvar no Banco de Dados
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = (
            "INSERT INTO chamados(cliente_nome, cliente_email, "
            "cliente_whatsapp, servico_titulo, descricao) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        cursor.execute(sql, (nome, email, whatsapp, servico, descricao))
        conn.commit()
        print(f"✅ Novo chamado recebido de: {nome}")
    except Exception as e:
        print(f"❌ Erro ao salvar chamado: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    # * 3. Redirecionar para uma página de agradecimento
    # * (ou voltar para a home)
    return """<h1>Solicitação enviada!</h1><p>Em breve entraremos em contato.
            </p><a href='/'>Voltar</a>"""


if __name__ == "__main__":
    # Prepara a estrutura
    inicializar_banco()

    # Valida a fiação
    executar_autoteste()

    # Sobe o servidor
    print("\n🚀 Servidor subindo em http://localhost:5000")
    app.run(debug=True)
