from flask import Flask, render_template, request, redirect
from database import inicializar_banco, executar_autoteste, get_db_connection
from flask import session, flash, url_for
from werkzeug.security import check_password_hash

app.secret_key = "N3v3rM3ssTh@tSh1tB0y"

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')


@app.route('/')
def home():
    return render_template('index.html')


# * Recebe  os dados do formulário para gravar no banco.
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


@app.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # *diconary=True facilita o uso no HTML

    try:
        cursor.execute("SELECT * FROM chamados ORDER BY data_criacao DESC")
        chamados = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar chamados: {e}")
        chamados = []
    finally:
        cursor.close()
        conn.close()

    return render_template('admin.html', chamados=chamados)


@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM chamados WHERE id = %s", (id,))
        conn.commit()
        print(f"🗑️ Chamado {id} excluído com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao excluir: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')


@app.route('/assumir/<int:id>', methods=['POST'])
def assumir_chamado(id):
    # * Por equanto, fixamos o ID 1
    # * No futuro, usaremos o di fo ténico logado: sesion[user_id]
    id_tecnico = 1

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = (
            "UPDATE chamados "
            "SET status = 'progresso'. tecnico_id = %s"
            "WHERE id = %s"
        )
        cursor.execute(sql, (id_tecnico, id))
        conn.commit()
        print(f"🛠️ Chamado {id} assumido pelo técnico {id_tecnico}")
    except Exception as e:
        print(f"❌ Erro ao assumir chamado: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        if usuario and check_password_hash(usuario['senha_hash'], senha):
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_cargo'] = usuario['cargo']
            return redirect('/admin')
        else:
            flash('E-mail ou senha incorretos!', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == "__main__":
    # Prepara a estrutura
    inicializar_banco()

    # Valida a fiação
    executar_autoteste()

    # Sobe o servidor
    print("\n🚀 Servidor subindo em http://localhost:5000")
    app.run(debug=True)
