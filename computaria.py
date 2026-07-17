import sys
import time
import sqlite3
from datetime import datetime
import serial
import serial.tools.list_ports


def encontrar_porta_arduino():
    """Varre as portas USB do computador para encontrar o Arduino automaticamente."""
    portas = list(serial.tools.list_ports.comports())
    
    # Palavras-chave comuns para placas Arduino
    palavras_chave = ["arduino", "usb", "ch340", "ftdi"]
    
    for porta in portas:
        descricao = porta.description.lower()
        # Se achar alguma palavra-chave na descrição da porta, seleciona ela
        if any(keyword in descricao for keyword in palavras_chave):
            print(f"🔌 Arduino encontrado na porta: {porta.device} ({porta.description})")
            return porta.device
            
    # Se não achar nada específico, mas houver portas ativas, pega a primeira disponível
    if portas:
        print(f"⚠️ Nenhum Arduino específico identificado. Tentando a primeira porta ativa: {portas[0].device}")
        return portas[0].device
        
    return None


def inicializar_banco():
    """Cria a tabela no banco de dados se ela não existir."""
    con = sqlite3.connect("umidade.db")
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS umidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            umidade INTEGER
        )
    """)
    con.commit()
    return con


def main():
    # 1. Encontra a porta automaticamente
    porta_arduino = encontrar_porta_arduino() 
    
    if not porta_arduino:
        print("❌ Erro: Nenhum Arduino ou dispositivo USB detectado. Verifique o cabo!")
        sys.exit()

    # 2. Inicializa conexões
    try:
        arduino = serial.Serial(porta_arduino, 9600, timeout=1)
        # Limpa o buffer inicial para evitar ler lixo de memória do Arduino
        arduino.reset_input_buffer() 
    except Exception as e:
        print(f"❌ Erro ao abrir a porta serial {porta_arduino}: {e}")
        sys.exit()

    con = inicializar_banco()
    cursor = con.cursor()

    print("📡 Lendo dados do sensor (Pressione Ctrl+C para parar)...")
    print("-" * 50)

    # 3. Loop de leitura
    try:
        while True:
            # Lê a linha enviada pelo Arduino
            if arduino.in_waiting > 0:
                dado = arduino.readline().decode().strip()

                if not dado:
                    continue

                if dado == "SEM SOLO!":
                    print("⚠️ Sensor fora do solo")
                    continue

                try:
                    umidade = int(dado)
                    data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    # Salva no banco de dados
                    cursor.execute(
                        "INSERT INTO umidade(data_hora, umidade) VALUES (?,?)",
                        (data, umidade)
                    )
                    con.commit()

                    print(f"💾 {data} -> {umidade}%")

                except ValueError:
                    # Ignora se receber algum caractere corrompido que não seja número
                    pass
            
            # Pausa curta para não estressar o processador do PC
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n👋 Programa encerrado pelo usuário.")

    finally:
        # Garante o fechamento correto dos recursos
        arduino.close()
        con.close()
        print("🔌 Conexões com Arduino e Banco de Dados fechadas com segurança.")


if __name__ == "__main__":
    main()