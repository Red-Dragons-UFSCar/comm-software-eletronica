import serial
import time
import threading
import struct 

# =============================================================================
#  CLASSE PARA GERENCIAR A COMUNICAÇÃO SERIAL
# =============================================================================

class ComunicacaoSerial:
    def __init__(self, porta, baudrate=115200, timeout=1):
        """Inicializa a comunicação serial e a thread de leitura."""
        self.ser = None
        try:
            self.ser = serial.Serial(porta, baudrate, timeout=timeout)
            print(f"Porta serial '{porta}' aberta com sucesso a {baudrate} bps.")
        except serial.SerialException as e:
            print(f"ERRO: Não foi possível abrir a porta serial '{porta}'.")
            print(f"Detalhe do erro: {e}")
            print("Verifique se a porta está correta e não está sendo usada por outro programa.")
            raise

        self.dados_recebidos = {}
        self.rodando = True
        
        self.thread_leitura = threading.Thread(target=self._ler_dados_serial)
        self.thread_leitura.daemon = True
        self.thread_leitura.start()

    def _ler_dados_serial(self):
        """
        Método executado em segundo plano pela thread para ler e processar dados.
        """
        while self.rodando:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    linha_bytes = self.ser.readline()
                    linha_str = linha_bytes.decode('utf-8').strip()
                    linha_str = linha_str.rstrip('\x00')

                    if not linha_str:
                        continue

                    print(f"Recebido: '{linha_str}'")
                    
                    partes = linha_str.split(',')

                    if len(partes) >= 2 and len(partes) % 6 == 0:
                        for i in range(0, len(partes), 6):
                            bloco = partes[i:i+6]
                            try:
                                id_robo = int(bloco[0])
                                velocidades = [float(v) for v in bloco[1:5]]
                                latencia = float(bloco[5])

                                self.dados_recebidos[id_robo] = {
                                    'velocidades': velocidades,
                                    'latencia': latencia,
                                    'timestamp': time.time()
                                }
                            except (ValueError, IndexError):
                                print(f"  -> Aviso: Bloco de dados mal formatado: {bloco}")

                    else:
                        self.dados_recebidos['raw'] = linha_str

                except UnicodeDecodeError:
                    print(f"  -> Aviso: Erro de decodificação de bytes. Dados recebidos podem estar corrompidos.")
                except Exception as e:
                    print(f"  -> Erro inesperado na thread de leitura: {e}")
            
            time.sleep(0.01)

    # --- 2. ALTERAÇÃO PRINCIPAL NA CLASSE ---
    def enviar_comando(self, comando):
        """Envia uma string de comando ou um objeto de bytes para a porta serial."""
        if self.ser and self.ser.is_open:
            dados_para_enviar = None
            
            # Se o comando for uma string, codifique-o como antes.
            if isinstance(comando, str):
                if not comando.endswith('\n'):
                    comando += '\n'
                dados_para_enviar = comando.encode('utf-8')
            
            # Se o comando já for bytes, use-o diretamente.
            elif isinstance(comando, bytes):
                dados_para_enviar = comando
            
            else:
                print(f"ERRO: Tipo de dado '{type(comando)}' não pode ser enviado.")
                return

            try:
                self.ser.write(dados_para_enviar)
                # print(f"Enviado: {dados_para_enviar}") # Debug de envio
            except serial.SerialException as e:
                print(f"ERRO ao enviar dados: {e}")

    def get_dados(self, id_robo):
        """Retorna os últimos dados recebidos para um ID específico."""
        return self.dados_recebidos.get(id_robo)

    def fechar(self):
        """Fecha a porta serial e termina a thread de forma segura."""
        print("Fechando a comunicação serial...")
        self.rodando = False
        self.thread_leitura.join()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Porta serial fechada.")

# =============================================================================
#  EXEMPLO DE USO NO SCRIPT PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    PORTA_SERIAL = "COM11" 
    BAUDRATE = 115200

    comunicador = None
    try:
        comunicador = ComunicacaoSerial(PORTA_SERIAL, BAUDRATE)
        
        id_robo_alvo = 0
        contador = 0

        while True:
            # --- 3. ALTERAÇÃO PRINCIPAL NO LOOP ---
            
            # Crie uma lista com os 15 inteiros que você quer enviar
            valores_para_enviar = [666, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
            
            # Defina o formato: 15 inteiros (i) de 32 bits em ordem de bytes little-endian (<)
            # Little-endian é o padrão para processadores ARM (como o STM32)
            formato = '<15i'
            
            # Empacote os valores em um objeto de bytes
            comando_em_bytes = struct.pack(formato, *valores_para_enviar)
            
            # Envia o comando em formato de bytes
            comunicador.enviar_comando(comando_em_bytes)
            
            dados_atuais = comunicador.get_dados(id_robo_alvo)
            
            print("-" * 30)
            if dados_atuais:
                print(f"Últimos dados recebidos do Robô {id_robo_alvo}:")
                print(f"  - Velocidades: {dados_atuais['velocidades']}")
                print(f"  - Latência: {dados_atuais['latencia']:.4f} s")
                print(f"  - Recebido há: {time.time() - dados_atuais['timestamp']:.2f} s")
            else:
                print(f"Aguardando dados do Robô {id_robo_alvo}...")

            contador += 1
            time.sleep(0.1)

    except serial.SerialException:
        print("Programa encerrado devido a falha na porta serial.")
    except KeyboardInterrupt:
        print("\nPrograma interrompido pelo usuário.")
    finally:
        if comunicador:
            comunicador.fechar()
