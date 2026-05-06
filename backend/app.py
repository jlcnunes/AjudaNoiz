from flask import Flask, render_template, request, redirect
from database import inicializar_banco, executar_autoteste, get_db_connection
from flask import session, flash, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from utilitarios import calcular_total_fatura
import pdfkit

app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = "N3v3rM3ssTh@tSh1tB0y"

@app.template_filter('brl')
def brl_filter(valor):
    try:
        float_valor = float(valor) # Garante que é um número
        return f"{float_valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return valor # Se não for número, retorna o que era antes

        
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


def eh_dia_util(data):
    # 0 = Segunda, 4 = Sexta. 5 e 6 são Sábado/Domingo.
    if data.weekday() > 4:
        return False
    # Lista básica de feriados fixos (Pode ser expandida)
    feriados = ['01-01', '21-04', '01-05', '07-09', '12-10', '02-11', '15-11', '25-12']
    return data.strftime('%d-%m') not in feriados


def verificar_disponibilidade_tecnico(tecnico_id, data_hora):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM agendamentos 
        WHERE tecnico_id = %s AND data_hora = %s AND status = 'Confirmado'
    ''', (tecnico_id, data_hora))
    conflito = cursor.fetchone()
    cursor.close()
    conn.close()
    return conflito is None

def obter_valor_hora():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'valor_hora_tecnica'")
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return float(res['valor']) if res else 150.00 # Retorna 150.00 se não achar no banco

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
    deseja_agendar = request.form.get('deseja_agendar') # 'SIM' ou 'NÃO'
    data_proposta = request.form.get('data_proposta') # Vem do seu input hidden

    # --- LÓGICA DE STATUS AUTOMÁTICO ---
    # Se o cliente escolheu "SIM" e forneceu uma data, o status é "Agendado".
    # Caso contrário, o status padrão é "Novo".
    status_inicial = 'Novo'
    if deseja_agendar == 'SIM' and data_proposta:
        status_inicial = 'Ag_pendente'
        print(f"💥 O status inicial é: {status_inicial}")
    else:
        data_proposta = None
    
    # * 2. Salvar no Banco de Dados
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Lógica de Cliente (Mantida do seu original)
        cursor.execute('SELECT id FROM clientes WHERE email = %s', (email,))
        cliente_existente = cursor.fetchone()
        if cliente_existente:
            cliente_id = cliente_existente['id']
            cursor.execute('UPDATE clientes SET ativo = 1 WHERE id = %s', (cliente_id,))
        else:
            cursor.execute("INSERT INTO clientes (nome, email, whatsapp) VALUES (%s, %s, %s)", (nome, email, whatsapp))
            cliente_id = cursor.lastrowid

        # INSERT com o status "Agendamento Pendente" ou "Novo"
        sql_chamado = """
            INSERT INTO chamados (cliente_id, cliente_nome, cliente_email, cliente_whatsapp,
            servico_titulo, descricao, deseja_agendar, data_proposta, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_chamado, (
            cliente_id, nome, email, whatsapp, servico, 
            descricao, deseja_agendar, data_proposta, status_inicial
        ))
        
        chamado_id = cursor.lastrowid
        conn.commit()

        # * 3. Envio de Notificação por E-mail
        try:
            texto_agendamento = ""
            if status_inicial == 'Agendado':
                # Converte a string da data para um formato bonito no e-mail
                dt = datetime.strptime(data_proposta, '%Y-%m-%dT%H:%M')
                texto_agendamento = f"\n📅 Seu pré-agendamento foi solicitado para: {dt.strftime('%d/%m/%Y às %H:%M')}\n"

            assunto_email = f"🚀 Chamado #{chamado_id} Recebido"
            corpo_email = f"""Olá {nome}, tudo bem? 👋
        
                Recebemos sua solicitação!
                🆔 Chamado: #{chamado_id}
                🔧 Serviço: {servico}
                {texto_agendamento}
                Nossa equipe técnica já foi alertada e em breve entraremos em contato. 👨‍💻
                Equipe AjudaNoiz ⚡"""
        
            enviar_email_notificacao(email, assunto_email, corpo_email)
        
        except Exception as e_mail:
            print(f"⚠️ Erro ao enviar e-mail: {e_mail}")

        return render_template('sucesso.html', chamado_id=chamado_id)

    except Exception as e:
        print(f"❌ Erro ao processar envio: {e}")
        conn.rollback()
        return f"Erro: {e}"
    finally:
        cursor.close()
        conn.close()

@app.route('/admin')
def admin():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # Define o limite por página
    LIMITE = 10 
    # Pega a página atual da URL, padrão é 1
    pagina = request.args.get('page', 1, type=int)
    offset = (pagina - 1) * LIMITE

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Conta o total de chamados para saber quantas páginas existem
        cursor.execute("SELECT COUNT(*) as total FROM chamados WHERE ativo = 1 AND data_exclusao IS NULL")
        total_chamados = cursor.fetchone()['total']
        total_paginas = (total_chamados + LIMITE - 1) // LIMITE

        # 2. Busca apenas os chamados daquela página específica
        sql = """
            SELECT ch.*, ag.data_hora as data_agendada
            FROM chamados ch
            LEFT JOIN agendamentos ag ON ch.id = ag.chamado_id
            WHERE ch.ativo = 1 AND ch.data_exclusao IS NULL 
            ORDER BY ch.data_criacao DESC 
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, (LIMITE, offset))
        chamados = cursor.fetchall()
        
    except Exception as e:
        print(f"❌ Erro na paginação: {e}")
        chamados = []
        total_paginas = 1
    finally:
        cursor.close()
        conn.close()

    return render_template('admin.html', 
                           chamados=chamados, 
                           pagina_atual=pagina, 
                           total_paginas=total_paginas)


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
        # 1. Busca os dados do cliente ANTES de desativar
        cursor.execute('''
            SELECT c.nome, c.email 
            FROM chamados ch
            JOIN clientes c ON ch.cliente_id = c.id
            WHERE ch.id = %s
        ''', (id,))
        dados = cursor.fetchone()

        # 2. Em vez de DELETE, fazemos UPDATE (Soft Delete)
        from datetime import datetime
        agora = datetime.now()
        
        # Define ativo = 0 e preenche a data de exclusão para o /arquivo
        cursor.execute('''
            UPDATE chamados 
            SET ativo = 0, data_exclusao = %s 
            WHERE id = %s
        ''', (agora, id))
        
        conn.commit()

        # 3. Notifica o cliente sobre o cancelamento/arquivamento
        if dados:
            assunto = f"❌ Chamado #{id}: Cancelado/Excluído."
            corpo = f"""Olá {dados['nome']},
            
            Informamos que o seu chamado número #{id} foi removido do nosso painel de atendimento ativo.

            Se isso foi um erro ou se você ainda precisa de suporte, por favor, abra uma nova solicitação em nosso site.

            Atenciosamente,
            Equipe AjudaNoiz ⚡"""
            
            enviar_email_notificacao(dados['email'], assunto, corpo)

        # 4. Registra no histórico que foi arquivado
        registrar_log(id, "Chamado arquivado/excluído do painel principal")
        
        flash(f"Chamado #{id} movido para o arquivo com sucesso!", "success")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao arquivar: {e}")
        flash("Erro ao processar a exclusão.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/admin')


@app.route('/assumir/<int:id>', methods=['POST'])
def assumir_chamado(id):
    if 'usuario_id' not in session:
        return redirect('/login')

    tecnico_id = session['usuario_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Busca dados do chamado, cliente e se já existe agendamento
        cursor.execute('''
            SELECT c.nome, c.email, ch.status, ch.deseja_agendar, ch.data_proposta,
                   (SELECT COUNT(*) FROM agendamentos ag WHERE chamado_id = ch.id) as ja_agendado
            FROM chamados ch
            JOIN clientes c ON ch.cliente_id = c.id
            WHERE ch.id = %s
        ''', (id,))
        dados = cursor.fetchone()

        if not dados:
            flash("Chamado não encontrado.", "danger")
            return redirect('/admin')

        # Inicializa a variável para evitar o erro de "not defined"
        status_final = 'Em progresso' 

        # --- LÓGICA DE AGENDAMENTO ---
        # Se já foi agendado antes ou se é um novo pedido de agendamento[cite: 12, 13]
        if dados['ja_agendado'] > 0 or (dados['deseja_agendar'] == 'SIM' and dados['data_proposta']):
            status_final = 'Agendado'
            
            # Se é a primeira vez assumindo e não está na tabela de agendamentos, insere[cite: 13]
            if dados['ja_agendado'] == 0:
                data_hora = dados['data_proposta']
                if not verificar_disponibilidade_tecnico(tecnico_id, data_hora):
                    flash(f"❌ Conflito: Você já tem compromisso para este horário.", "danger")
                    return redirect('/admin')
                
                cursor.execute("INSERT INTO agendamentos (chamado_id, tecnico_id, data_hora) VALUES (%s, %s, %s)",
                               (id, tecnico_id, data_hora))

        # 2. Atualiza o chamado no banco
        cursor.execute("UPDATE chamados SET tecnico_id = %s, status = %s WHERE id = %s", 
                    (tecnico_id, status_final, id))
        conn.commit()
        
        # 3. Preparação e envio do e-mail[cite: 12]
        if status_final == 'Agendado':
            assunto = f"📅 Chamado #{id}: Agendamento Confirmado."
            data_f = dados['data_proposta'].strftime('%d/%m/%Y às %H:%M')
            corpo = f"Olá {dados['nome']},\n\nSeu agendamento para o chamado #{id} foi confirmado para {data_f}.\n\nTécnico: {session['usuario_nome']}\n\nEquipe AjudaNoiz ⚡"
        else:
            assunto = f"👨‍💻 Chamado #{id}: Técnico Atribuído."
            corpo = f"Olá {dados['nome']}, o técnico {session['usuario_nome']} assumiu seu chamado e já está trabalhando nele! 🚀"

        enviar_email_notificacao(dados['email'], assunto, corpo)
        
        # 4. Log e Feedback[cite: 12]
        texto_log = "Retomou" if dados['status'] == 'Suspenso' else "Assumiu"
        registrar_log(id, f"{texto_log} o chamado (Status: {status_final})")
        
        flash(f"Chamado #{id} alterado para {status_final}!", "success")

    except Exception as e:
        print(f"❌ Erro ao assumir/retomar: {e}")
        conn.rollback()
        flash("Erro ao processar a operação.", "danger")
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
        assunto = f"⏳ Chamado #{id}: Suspenso."
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
            assunto = f"✅ Chamado #{id}: Chamado Concluído."
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
            assunto = f"🛠️ Chamado #{id}: Nova atualização"
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


@app.route('/admin/chamado/<int:id>/fatura')
def preparar_fatura(id):
    # 1. Busca os detalhes do chamado e do cliente para o cabeçalho da fatura
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT ch.id, ch.servico_titulo, ch.data_criacao, c.nome, c.email, c.whatsapp 
        FROM chamados ch 
        JOIN clientes c ON ch.cliente_id = c.id 
        WHERE ch.id = %s
    ''', (id,))
    chamado = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if not chamado:
        flash("Chamado não encontrado para gerar fatura.", "danger")
        return redirect('/admin')

    # 2. Usa a função do utilitarios.py para os cálculos financeiros
    financeiro = calcular_total_fatura(id)

    # 3. Aviso o usuário que não foipossível calcula a fatura.
    if not financeiro:
        flash("Não foi possível calcular a fatura. Certifique-se de que existem notas técnicas com tempo registrado.", "warning")
        return redirect(f'/admin/chamado/{id}')

    # 4 Renderiza o template que será transformado em PDF
    return render_template('fatura_template.html', chamado=chamado, financeiro=financeiro, data_atual=datetime.now().strftime('%d/%m/%Y'))


@app.route('/admin/chamado/<int:id>/enviar_fatura')
def enviar_fatura_email(id):
    # 1. Coleta os dados (Lógica similar à que discutimos antes)
    from utilitarios import calcular_total_fatura
    financeiro = calcular_total_fatura(id)
    
    # Busca dados do cliente (ID, nome, email)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT ch.id, ch.servico_titulo, ch.data_criacao, c.nome, c.email, c.whatsapp 
        FROM chamados ch 
        JOIN clientes c ON ch.cliente_id = c.id 
        WHERE ch.id = %s
    """, (id,))
    cliente = cursor.fetchone()
    
    # 2. Gera o HTML do PDF
    html_fatura = render_template('fatura_template.html', 
                                 chamado=cliente, 
                                 financeiro=financeiro, 
                                 data_atual=datetime.now().strftime('%d/%m/%Y'))

    # 3. Converte HTML para PDF
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    pdf = pdfkit.from_string(html_fatura, False, configuration=config)

    # 4. Cria e envia o E-mail
    msg = Message(f"Fatura do Atendimento #{id} - AjudaNoiz TI",
                  recipients=[cliente['email']])
    msg.body = f"Olá {cliente['nome']},\n\nSegue em anexo a fatura referente ao seu atendimento técnico.\n\nTotal: R$ {financeiro['valor_total']}"
    
    # Anexa o PDF (nome do arquivo, tipo mime, conteúdo)
    msg.attach(f"fatura_ajudanoiz_{id}.pdf", "application/pdf", pdf)
    
    try:
        mail.send(msg)
        flash(f"Fatura enviada com sucesso para {cliente['email']}!", "success")
    except Exception as e:
        flash(f"Erro ao enviar e-mail: {str(e)}", "danger")

    return redirect(f'/chamado/{id}')


@app.route('/admin/configuracoes')
def exibir_configuracoes():
    # Busca o valor atual para exibir no formulário
    from utilitarios import obter_valor_hora # Vamos adicionar essa no utilitarios.py
    valor = obter_valor_hora()
    return render_template('configuracoes.html', valor_hora=valor)


@app.route('/admin/configuracoes/salvar', methods=['POST'])
def salvar_configuracoes():
    novo_valor = request.form.get('valor_hora')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Atualiza ou insere a chave de configuração
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor) 
        VALUES ('valor_hora_tecnica', %s)
        ON DUPLICATE KEY UPDATE valor = %s
    """, (novo_valor, novo_valor))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash("Configurações atualizadas com sucesso!", "success")
    return redirect('/admin/configuracoes')


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
