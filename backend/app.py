from flask import Flask, render_template, request, redirect
from database import inicializar_banco, executar_autoteste, get_db_connection
from flask import session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

from flask_mail import Mail, Message  # Adicione no topo


app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = "N3v3rM3ssTh@tSh1tB0y"


# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ajudanoizapp@gmail.com'
app.config['MAIL_PASSWORD'] = 'zhsv xqnh bclk cyme' # 16 dígitos sem espaços
app.config['MAIL_DEFAULT_SENDER'] = ('AjudaNoiz', 'ajudanoizapp@gmail.com')

mail = Mail(app)


def enviar_email_notificacao(destinatario, assunto, corpo_texto):
    try:
        msg = Message(subject=assunto, recipients=[destinatario])
        msg.body = corpo_texto
        mail.send(msg)
        print(f"📧 Notificação enviada para {destinatario}")
    except Exception as e:
        print(f"⚠️ Falha ao enviar notificação: {e}")


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
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('SELECT id, nome, whatsapp FROM clientes WHERE email = %s', (email,))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            cliente_id = cliente_existente['id']
            cursor.execute('UPDATE clientes SET ativo = 1 WHERE id = %s', (cliente_id,))

            if cliente_existente['whatsapp'] != whatsapp or cliente_existente['nome'] != nome:
                sql_update = "UPDATE clientes SET nome = %s, whatsapp = %s WHERE id = %s"
                cursor.execute(sql_update, (nome, whatsapp, cliente_id))
                print(f"🔄 Dados do cliente {cliente_id} atualizados (WhatsApp/Nome).")

        else:
            sql_novo_cliente = "INSERT INTO clientes (nome, email, whatsapp) VALUES (%s, %s, %s)"
            cursor.execute(sql_novo_cliente, (nome, email, whatsapp))
            cliente_id = cursor.lastrowid
            print(f"✨ Novo cliente cadastrado com ID: {cliente_id}")

        sql_chamado = """
            INSERT INTO chamados (cliente_id, cliente_nome, cliente_email,
            cliente_whatsapp, servico_titulo, descricao)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_chamado, (cliente_id, nome, email, whatsapp, servico, descricao))
        protocolo = cursor.lastrowid 

        conn.commit()

        try:
            assunto_email = f"🚀 Protocolo de Atendimento: #{protocolo}"
            corpo_email = f"""Olá {nome}, tudo bem? 👋
        
                Passando para avisar que o seu chamado já caiu aqui no nosso sistema! 📥
                🆔 Protocolo: #{protocolo}
                🔧 Serviço: {servico}

                Nossa equipe técnica já foi alertada e em breve entraremos em contato. 👨‍💻
                Equipe AjudaNoiz ⚡"""
        
            enviar_email_notificacao(email, assunto_email, corpo_email)
        
        except Exception as e_mail:
            print(f"⚠️ Erro ao enviar e-mail: {e_mail}")

        return render_template('sucesso.html', chamado_id=protocolo)

    except Exception as e:
        print(f"❌ Erro ao processar envio: {e}")
        conn.rollback()
        return f"Erro{e}"
    finally:
        cursor.close()
        conn.close()


@app.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # *diconary=True facilita o uso no HTML

    try:
        cursor.execute(
            "SELECT * FROM chamados "
            "WHERE ativo = 1 AND data_exclusao "
            "IS NULL ORDER BY data_criacao DESC"
            )
        chamados = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar chamados: {e}")
        chamados = []
    finally:
        cursor.close()
        conn.close()

    return render_template('admin.html', chamados=chamados)


def registrar_log(chamado_id, acao):
    usuario_id = session.get('usuario_id')  # *Pega o ID do admin logado.
    if not usuario_id:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """INSERT INTO historico_chamados
        (chamado_id, usuario_id, acao) VALUES (%s, %s, %s)"""
        cursor.execute(sql, (chamado_id, usuario_id, acao))
        conn.commit()
        print(f"✅ Log gravado no banco: {acao}")
    except Exception as e:
        print(f"❌ Erro ao gravar no banco: {e}")
    finally:
        cursor.close()
        conn.close()


@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Busca os dados do cliente ANTES de deletar o chamado
        cursor.execute('''
            SELECT c.nome, c.email 
            FROM chamados ch
            JOIN clientes c ON ch.cliente_id = c.id
            WHERE ch.id = %s
        ''', (id,))
        dados = cursor.fetchone()

        # 2. Executa a exclusão no banco
        cursor.execute("DELETE FROM chamados WHERE id = %s", (id,))
        conn.commit()

        # 3. Se o chamado existia, envia a notificação de cancelamento
        if dados:
            assunto = f"❌ Chamado #{id} Cancelado/Excluído"
            corpo = f"""Olá {dados['nome']},
            
            Informamos que o seu chamado de protocolo #{id} foi removido do nosso sistema.

            Se isso foi um erro ou se você ainda precisa de suporte, por favor, abra uma nova solicitação em nosso site.

            Atenciosamente,
            Equipe AjudaNoiz ⚡"""
            
            enviar_email_notificacao(dados['email'], assunto, corpo)

        flash(f"Chamado #{id} excluído com sucesso!", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao deletar: {e}")
        flash("Erro ao excluir chamado. Ele pode ter históricos vinculados.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')

@app.route('/assumir/<int:id>', methods=['POST'])
def assumir_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Busca dados do cliente E o status atual do chamado
        cursor.execute('''
            SELECT c.nome, c.email, ch.status 
            FROM chamados ch
            JOIN clientes c ON ch.cliente_id = c.id
            WHERE ch.id = %s
        ''', (id,))
        dados = cursor.fetchone()

        if not dados:
            flash("Chamado não encontrado.", "danger")
            return redirect('/admin')

        # 2. Define a mensagem de log e e-mail baseada no status anterior
        status_anterior = dados['status'].strip() if dados['status'] else ""
        
        if status_anterior == 'Suspenso':
            mensagem_log = "Retomou o atendimento (estava suspenso)"
            assunto = "🚀 Atendimento Retomado"
            corpo = f"Olá {dados['nome']}, o técnico {session['usuario_nome']} retomou o seu atendimento agora mesmo! ⚡"

        else:
            mensagem_log = "Assumiu o chamado e iniciou o atendimento"
            assunto = "👨‍💻 Técnico Atribuído"
            corpo = f"Olá {dados['nome']}, o técnico {session['usuario_nome']} já assumiu seu chamado e iniciou o diagnóstico! 🚀"

        # 3. Atualiza o banco
        cursor.execute("UPDATE chamados SET tecnico_id = %s, status = 'Em progresso' WHERE id = %s", 
                    (session['usuario_id'], id))
        conn.commit()
        
        # 4. Registra log e envia e-mail
        registrar_log(id, mensagem_log)
        enviar_email_notificacao(dados['email'], assunto, corpo)
        
        flash(f"Você assumiu o chamado #{id}!", "success")

    except Exception as e:
        print(f"❌ Erro ao assumir chamado: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')

@app.route('/suspender/<int:id>', methods=['POST'])
def suspender_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    # CORREÇÃO: Adicionado dictionary=True para poder usar dados['nome']
    cursor = conn.cursor(dictionary=True) 
    try:
        # 1. Busca os dados do cliente
        cursor.execute('''
            SELECT c.nome, c.email 
            FROM chamados ch
            JOIN clientes c ON ch.cliente_id = c.id
            WHERE ch.id = %s
        ''', (id,))
        dados = cursor.fetchone()

        if not dados:
            flash("Chamado não encontrado.", "danger")
            return redirect('/admin')

        # 2. ATUALIZA O STATUS NO BANCO (Faltava isso no seu script)
        cursor.execute("UPDATE chamados SET status = 'Suspenso' WHERE id = %s", (id,))
        conn.commit()

        # 3. Dispara o E-mail
        assunto = "⏳ Chamado Suspenso - AjudaNoiz"
        corpo = f"""Olá {dados['nome']}, 👋
        
        Passando para avisar que o seu chamado #{id} foi colocado em status de 'Suspenso' pelo técnico {session['usuario_nome']}. ⌛

        Isso geralmente acontece quando precisamos de alguma informação adicional ou aguardamos uma peça/software. 

        Fique tranquilo, assim que retomarmos o atendimento, você será avisado! ⚡"""

        enviar_email_notificacao(dados['email'], assunto, corpo)

        # 4. Grava o histórico (Timeline)
        registrar_log(id, "Suspendeu o chamado (Status: Suspenso)")
        
        flash(f"Chamado #{id} suspenso e cliente notificado.", "warning")

    except Exception as e:
        print(f"❌ Erro ao suspender: {e}")
        conn.rollback()
        flash("Erro ao processar suspensão.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')

@app.route('/concluir/<int:id>', methods=['POST'])
def concluir_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Busca o e-mail antes de atualizar
        cursor.execute("SELECT cliente_email, cliente_nome FROM chamados WHERE id = %s", (id,))
        info = cursor.fetchone()
        
        # 2. Atualiza o status
        cursor.execute("UPDATE chamados SET status = 'Concluído' WHERE id = %s", (id,))
        conn.commit()

        if info:
            assunto = f"✅ Chamado #{id} Concluído!"
            corpo = f"""Olá {info[1]}! Seu atendimento foi finalizado com sucesso. 🏁
    
                Caso o problema persista ou precise de algo novo, estamos à disposição.
                Obrigado por confiar na AjudaNoiz! ⚡"""
            enviar_email_notificacao(info[0], assunto, corpo)

        # *Grava o histórico
        registrar_log(id, "Concluiu o chamado e mudou status para Concluído")
    except Exception as e:
        print(f"❌ Erro ao concluir: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')


@app.route('/chamado/<int:id>')
def ver_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Busca os detalhes do chamado
    cursor.execute("SELECT * FROM chamados WHERE id = %s", (id,))
    chamado = cursor.fetchone()

    # 2. Busca o histórico (Timeline)
    cursor.execute("""
        SELECT h.*, u.nome as nome_usuario 
        FROM historico_chamados h
        JOIN usuarios u ON h.usuario_id = u.id
        WHERE h.chamado_id = %s
        ORDER BY h.data_acao DESC
    """, (id,))
    historico = cursor.fetchall()

    # 3. NOVO: Soma o tempo total gasto em atividades
    cursor.execute("SELECT SUM(tempo_gasto) as total_minutos FROM atividades WHERE chamado_id = %s", (id,))
    resultado_tempo = cursor.fetchone()
    total_minutos = resultado_tempo['total_minutos'] or 0
    
    # Converte para formato horas:minutos para exibição
    horas = total_minutos // 60
    minutos_restantes = total_minutos % 60
    tempo_formatado = f"{horas}h {minutos_restantes}min"

    cursor.close()
    conn.close()

    return render_template('detalhes_chamado.html', 
                           chamado=chamado, 
                           historico=historico, 
                           tempo_total=tempo_formatado)


@app.route('/arquivo')
def visualizar_arquivo():
    if 'usuario_id' not in session:
        return redirect('/login')

    # * Captura os filtros da URL (se existirem)
    f_id = request.args.get('id')
    f_cliente = request.args.get('cliente')
    f_tecnico = request.args.get('tecnico')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # * Base da query: apenas chamados desativados
    sql = """
        SELECT c.*, u.nome as nome_tecnico
        FROM chamados c
        LEFT JOIN usuarios u ON c.tecnico_id = u.id
        WHERE (c.ativo = 0 OR c.data_exclusao IS NOT NULL)
    """
    params = []

    # * Filtros dinâmicos
    if f_id:
        sql += " AND c.id = %s"
        params.append(f_id)
    if f_cliente:
        sql += " AND c.cliente_nome LIKE %s"
        params.append(f"%{f_cliente}%")
    if f_tecnico:
        sql += " AND u.nome LIKE %s"
        params.append(f"%{f_tecnico}%")

    sql += " ORDER BY c.data_criacao DESC"

    try:
        cursor.execute(sql, params)
        chamados_excluidos = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro SQL no Filtro do Arquivo: {e}")
        return f"Erro ao filtrar: {e}", 500
    finally:
        cursor.close()
        conn.close()

    return render_template('arquivo.html', chamados=chamados_excluidos)

@app.route('/admin/clientes')
def listar_clientes():
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca clientes e conta o total de chamados vinculados a cada um
        sql = """
            SELECT c.id, c.nome, c.email, c.whatsapp, c.data_cadastro,
                    COUNT(ch.id) as total_chamados
            FROM clientes c
            LEFT JOIN chamados ch ON c.id = ch.cliente_id
            WHERE c.ativo = 1
            GROUP BY c.id
            ORDER BY c.data_cadastro DESC
        """
        cursor.execute(sql)
        clientes = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao listar clientes: {e}")
        clientes = []
    finally:
        cursor.close()
        conn.close()

    return render_template('clientes.html', clientes=clientes)


@app.route('/admin/clientes/salvar', methods=['POST'])
def salvar_cliente():
    if 'usuario_id' not in session:
        return redirect('/login')

    cliente_id = request.form.get('id')  # Se vier ID, é edição. Se não, é novo.
    nome = request.form.get('nome')
    email = request.form.get('email').strip().lower()
    whatsapp = request.form.get('whatsapp')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if cliente_id:
            # UPDATE
            sql = """UPDATE clientes SET nome = %s, email = %s,
            whatsapp = %s WHERE id = %s"""
            cursor.execute(sql, (nome, email, whatsapp, cliente_id))
            flash("Cliente atualizado com sucesso!", "success")
        else:
            # INSERT
            sql = "INSERT INTO clientes (nome, email, whatsapp) VALUES (%s, %s, %s)"
            cursor.execute(sql, (nome, email, whatsapp))
            flash("Novo cliente cadastrado!", "success")

        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao salvar cliente: {e}")
        flash("Erro ao salvar: E-mail já cadastrado ou erro no banco.", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect('/admin/clientes')


@app.route('/admin/clientes/buscar/<int:id>')
def buscar_clientes(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes WHERE id = %s", (id,))
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()
    return cliente  # Retonar JSON


@app.route('/admin/clientes/excluir/<int:id>', methods=['POST'])
def excluir_cliente(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Soft Delete: Apenas marca como inativo
        cursor.execute("UPDATE clientes SET ativo = 0 WHERE id = %s", (id,))
        conn.commit()
        flash("Cliente desativado com sucesso! O histórico foi preservado.", "sucesso")
    except Exception as e:
        conn.rollback()
        flash(f"❌ Erro ao desativar cliente: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect('/admin/clientes')


@app.route('/chamado/<int:id>/nota', methods=['POST'])
def adicionar_nota(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    nota = request.form.get('nota')
    tempo = request.form.get('tempo', 0)

    # 1. Preparando o resumo para o histórico
    nota_resumo = nota[:500] + "..." if len(nota) > 500 else nota
    acao_para_historico = f"Nota Técnica ({tempo} min): {nota_resumo}"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Usamos dictionary para facilitar
    try:
        # --- NOVIDADE: BUSCA O E-MAIL E NOME DO CLIENTE ---
        cursor.execute('''
            SELECT c.nome, c.email 
            FROM clientes c 
            JOIN chamados ch ON c.id = ch.cliente_id 
            WHERE ch.id = %s
        ''', (id,))
        cliente = cursor.fetchone()

        # 2. Registra na tabela ATIVIDADES (Nota completa)
        sql_atv = "INSERT INTO atividades (chamado_id, descricao, tempo_gasto) VALUES (%s, %s, %s)"
        cursor.execute(sql_atv, (id, nota, tempo))

        # 3. Registra na tabela HISTORICO_CHAMADOS (Resumo)
        sql_hist = "INSERT INTO historico_chamados (chamado_id, usuario_id, acao) VALUES (%s, %s, %s)"
        cursor.execute(sql_hist, (id, session['usuario_id'], acao_para_historico))

        conn.commit()

        # --- NOVIDADE: DISPARA O E-MAIL SE O CLIENTE FOR ENCONTRADO ---
        if cliente:
            assunto = f"🛠️ Atualização no Chamado #{id}"
            corpo = f"""Olá {cliente['nome']}, 👋
            
                Uma nova atualização técnica foi registrada no seu chamado:
                --------------------------------------------------
                "{nota_resumo}"
                --------------------------------------------------

                Tempo investido nesta etapa: {tempo} min.
                Nossa equipe continua trabalhando na sua solicitação. ⚡"""
            
            enviar_email_notificacao(cliente['email'], assunto, corpo)

        flash(f'Atendimento de {tempo} min registrado e e-mail enviado!', 'success')

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro na nota técnica: {e}")
        flash(f"Erro técnico: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('ver_chamado', id=id))

@app.route('/admin/usuarios')
def gerenciar_usuarios():
    if 'usuario_id' not in session or session.get('usuario_cargo') != 'admin':
        flash('Acesso restrito a administradores!', 'danger')
        return redirect('/admin')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome, email, cargo, data_cadastro FROM usuarios")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)


@app.route('/admin/usuarios/salvar', methods=['POST'])
def salvar_usuarios():
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')
    cargo = request.form.get('cargo')

    # Cripografa a senha anrtes de ser salva
    senha_hash = generate_password_hash(senha)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (nome, email, senha_hash, cargo) VALUES (%s, %s, %s, %s)",
        (nome, email, senha_hash, cargo))
        conn.commit()
        flash('Usuario cadastrado com sucesso!', 'sucesso')
    except Exception as e:
        conn.rollback()
        flash(f'❌ Erro ao cadastrar: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect('/admin/usuarios')


# Rota para excluir Usuários (Técnicos/Admins)
@app.route('/admin/usuarios/excluir/<int:id>', methods=['POST'])
def excluir_usuario(id):
    if 'usuario_id' not in session or session.get('usuario_cargo') != 'admin':
        flash('Acesso restrito!', 'danger')
        return redirect('/admin')

    # Impede que o admin logado exclua a si mesmo
    if id == session.get('usuario_id'):
        flash('Você não pode excluir sua própria conta!', 'danger')
        return redirect('/admin/usuarios')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        conn.commit()
        flash("Usuário removido da equipe!", "success")
    except Exception as e:
        conn.rollback()
        flash("❌ Erro: Este usuário pode estar vinculado a históricos de chamados.", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect('/admin/usuarios')


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
