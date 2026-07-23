
import sys
import time
import sqlite3
from datetime import datetime
import serial
import serial.tools.list_ports

print("=" * 60)
print("      BEM-VINDO AO SISTEMA DE MONITORAMENTO IoT")
print("           Monitoramento de Umidade do Solo")
print("=" * 60)

for i in range(5, 0, -1):
    print(f"Iniciando em {i} segundos...", end="\r")
    time.sleep(1)

print("\nSistema iniciado!\n")

# ==========================================
# DEFINIÇÃO DE LIMITES ACEITÁVEIS DO SOLO
# ==========================================
UMIDADE_MIN_SOLO = 60.0  # Abaixo disso: Solo Seco (Precisa Regar)
UMIDADE_MAX_SOLO = 80.0  # Acima disso: Solo Encharcado


def encontrar_porta_arduino():
    """Varre as portas USB do computador para encontrar o Arduino automaticamente."""
    portas = list(serial.tools.list_ports.comports())
    palavras_chave = ["arduino", "usb", "ch340", "ftdi"]
    
    for porta in portas:
        descricao = porta.description.lower()
        if any(keyword in descricao for keyword in palavras_chave):
            print(f" Arduino encontrado na porta: {porta.device} ({porta.description})")
            return porta.device
            
    if portas:
        print(f" Nenhum Arduino específico identificado. Tentando a primeira porta ativa: {portas[0].device}")
        return portas[0].device
        
    return None


def inicializar_banco():
    """Cria a tabela no banco de dados para registrar os dados de umidade do solo."""
    con = sqlite3.connect("monitoramento_solo_iot.db")
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leituras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            umidade_solo REAL,
            status TEXT
        )
    """)
    con.commit()
    return con


def determinar_status(umidade):
    """Define o texto do status de acordo com o nível de umidade."""
    if umidade < UMIDADE_MIN_SOLO:
        return "SOLO SECO"
    elif umidade > UMIDADE_MAX_SOLO:
        return "ENCHARCADO"
    else:
        return "IDEAL"


def verificar_alertas(umidade, status):
    """Gera alertas visuais no console com base no status do solo."""
    if status == "SEM SOLO":
        print("    ALERTA CRÍTICO: Sensor desconectado ou fora da terra!")
    elif status == "SOLO SECO":
        print(f"    ALERTA: Solo muito seco! ({umidade:.1f}% < {UMIDADE_MIN_SOLO}%) -> Irrigação necessária!")
    elif status == "ENCHARCADO":
        print(f"    ALERTA: Solo encharcado! ({umidade:.1f}% > {UMIDADE_MAX_SOLO}%)")
    else:
        print("    Solo em nível ideal de umidade.")


def gerar_relatorio_historico(cursor, limite=10):
    """Gera o relatório do histórico armazenado no SQLite."""
    print("\n" + "=" * 65)
    print(" RELATÓRIO DE MONITORAMENTO DE UMIDADE DO SOLO (IoT)")
    print("=" * 65)
    
    cursor.execute(
        "SELECT id, data_hora, umidade_solo, status FROM leituras ORDER BY id DESC LIMIT ?", 
        (limite,)
    )
    registros = cursor.fetchall()
    
    if registros:
        print(f"--- ÚLTIMAS {len(registros)} LEITURAS ---")
        for reg in registros:
            umi_str = f"{reg[2]:.1f}%" if reg[2] is not None else "N/A"
            print(f"ID: {reg[0]:<4} | Data: {reg[1]} | Umidade Solo: {umi_str:<6} | Status: {reg[3]}")
        
        cursor.execute("SELECT AVG(umidade_solo) FROM leituras WHERE status != 'SEM SOLO'")
        media_umi = cursor.fetchone()[0]
        
        print("-" * 65)
        if media_umi is not None:
            print(f" Média Geral (Solo Conectado) -> Umidade: {media_umi:.1f}%")
    else:
        print("Nenhum registro encontrado no banco de dados.")
        
    print("=" * 65 + "\n")


def main():
    porta_arduino = encontrar_porta_arduino() 
    
    if not porta_arduino:
        print(" Erro: Nenhum Arduino ou dispositivo USB detectado. Verifique o cabo!")
        sys.exit()

    try:
        arduino = serial.Serial(porta_arduino, 9600, timeout=1)
        arduino.reset_input_buffer() 
    except Exception as e:
        print(f" Erro ao abrir a porta serial {porta_arduino}: {e}")
        sys.exit()

    con = inicializar_banco()
    cursor = con.cursor()

    print("\n SISTEMA DE MONITORAMENTO DE SOLO INICIADO (Ctrl+C para parar)")
    print(f" Faixa ideal para o Solo: {UMIDADE_MIN_SOLO}% a {UMIDADE_MAX_SOLO}%")
    print("-" * 65)

    try:
        while True:
            if arduino.in_waiting > 0:
                dado = arduino.readline().decode().strip()

                if not dado:
                    continue

                data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # Trata a mensagem "SEM SOLO!"
                if dado == "SEM SOLO!":
                    umidade = None
                    status = "SEM SOLO"
                    
                    cursor.execute(
                        "INSERT INTO leituras (data_hora, umidade_solo, status) VALUES (?,?,?)",
                        (data, umidade, status)
                    )
                    con.commit()

                    print(f" [{data}] Status: {status}")
                    verificar_alertas(umidade, status)
                    continue

                try:
                    umidade = float(dado)
                    
                    # Define o status dinamicamente de acordo com o valor
                    status = determinar_status(umidade)

                    # Grava no banco de dados
                    cursor.execute(
                        "INSERT INTO leituras (data_hora, umidade_solo, status) VALUES (?,?,?)",
                        (data, umidade, status)
                    )
                    con.commit()

                    print(f" [{data}] Umidade Solo: {umidade:.1f}% | Status: {status}")
                    verificar_alertas(umidade, status)

                except ValueError:
                    pass
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n Sistema encerrado pelo usuário.")
        gerar_relatorio_historico(cursor)

    finally:
        arduino.close()
        con.close()
        print(" Conexões serial e banco de dados encerradas com segurança.")


if __name__ == "__main__":
    main()
