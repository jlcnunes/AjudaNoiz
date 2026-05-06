from database import get_db_connection

def obter_valor_hora():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'valor_hora_tecnica'")
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return float(res['valor']) if res else 150.00

def calcular_total_fatura(chamado_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Busca o valor da hora técnica configurado
        cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'valor_hora_tecnica'")
        res_config = cursor.fetchone()
        valor_hora = float(res_config['valor']) if res_config else 150.00

        # 2. Soma todo o tempo gasto (minutos) nas atividades deste chamado
        cursor.execute("SELECT SUM(tempo_gasto) as total_minutos FROM atividades WHERE chamado_id = %s", (chamado_id,))
        res_tempo = cursor.fetchone()
        total_minutos = float(res_tempo['total_minutos']) if res_tempo['total_minutos'] else 0.0

        # 3. Cálculo Matemático
        # Convertemos minutos para horas decimais (ex: 90 min = 1.5h)
        total_horas = total_minutos / 60
        valor_final = total_horas * valor_hora

        return {
            'minutos_totais': total_minutos,
            'tempo_total': round(total_horas, 2), 
            'horas_decimais': round(total_horas, 2),
            'valor_hora': valor_hora,
            'subtotal': round(valor_final, 2),  
            'valor_total': round(valor_final, 2)
        }

    except Exception as e:
        print(f"Erro ao calcular fatura: {e}")
        return None
    finally:
        cursor.close()
        conn.close()