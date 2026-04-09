from flask import Flask, render_template, request, redirect
from database import inicializar_banco, executar_autoteste, get_db_connection
from flask import session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = "N3v3rM3ssTh@tSh1tB0y"


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
    cursor = conn.cursor()
    try:
        from datetime import datetime
        agora = datetime.now()

        sql = "UPDATE chamados SET ativo = 0, data_exclusao = %s WHERE id = %s"
        cursor.execute(sql, (agora, id,))
        conn.commit()
        print(f"🗑️ Chamado {id} arquivado/excluído do painel principal!")

        # * Grava o histórico
        registrar_log(id, "Chamado arquivado/excluido do painel principal")
    except Exception as e:
        print(f"❌ Erro ao excluir: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')


@app.route('/assumir/<int:id>', methods=['POST'])
def assumir_chamado(id):
    # * Verifica se o usuário está logado
    if 'usuario_id' not in session:
        return redirect('/login')

    # * PEGA O ID REAL DO USUÁRIO LOGADO (Ex: 117)
    id_tecnico = session['usuario_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM chamados WHERE id = %s", (id,))
        chamado_atual = cursor.fetchone()

        sql = """
            UPDATE chamados SET status = 'Em progresso',
            tecnico_id = %s WHERE id = %s"""
        cursor.execute(sql, (id_tecnico, id,))
        conn.commit()

        if chamado_atual and chamado_atual['status'].strip() == 'Suspenso':
            mensagem_log = "Retomou o atendimento (estava suspenso)"
        else:
            mensagem_log = "Assumiu o chamado e iniciou o atendimento"

        # *Grava o histórico
        registrar_log(id, mensagem_log)
        print(f"✅ {mensagem_log} no chamado {id}")
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
    cursor = conn.cursor()
    try:
        # Usando 3 aspas para evitar erros de espaço e quebra de linha
        sql = """
            UPDATE chamados
            SET status = 'Suspenso'
            WHERE id = %s
        """
        cursor.execute(sql, (id,))
        conn.commit()
        print(f"⏳ Chamado {id} foi suspenso.")

        # *Grava o histórico
        registrar_log(id, "Suspendeu o chamado e mudou status para Suspenso")
    except Exception as e:
        print(f"❌ Erro ao suspender: {e}")
        conn.rollback()
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
        # Atualiza o status para 'concluido'
        sql = "UPDATE chamados SET status = 'Concluído' WHERE id = %s"
        cursor.execute(sql, (id,))
        conn.commit()

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
    print(f"DEBUG: Sessão atual: {session}")
    if 'usuario_id' not in session:
        return redirect('/login')

    nota = request.form.get('nota')
    tempo = request.form.get('tempo', 0) # Captura os minutos

    # Limita o texto da timeline para não quebrar o layout, 
    # mas mantém a nota completa na tabela atividades
    nota_resumo = nota[:500] + "..." if len(nota) > 500 else nota
    acao_para_historico = f"Nota Técnica ({tempo} min): {nota_resumo}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Registra na tabela atividades (onde o tempo é contabilizado)
        sql_atv = "INSERT INTO atividades (chamado_id, descricao, tempo_gasto) VALUES (%s, %s, %s)"
        cursor.execute(sql_atv, (id, nota, tempo))

        # 2. Registra na tabela HISTORICO_CHAMADOS (Aqui usamos o RESUMO)
        sql_hist = "INSERT INTO historico_chamados (chamado_id, usuario_id, acao) VALUES (%s, %s, %s)"
        cursor.execute(sql_hist, (id, session['usuario_id'], acao_para_historico))
        
        conn.commit()
        flash(f'Atendimento de {tempo} min registrado!', 'success')
    except Exception as e:
        conn.rollback()
        import traceback
        print("Detailed Error:")
        traceback.print_exc()
        flash(f"❌ Erro técnico: {e}", "danger")
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
