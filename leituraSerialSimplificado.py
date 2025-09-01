import serial
import time
import threading

# =============================================================================
#  CLASSE PARA GERENCIAR A COMUNICAÇÃO SERIAL
#  Baseada na sua classe, com um método adicional para envio de dados.
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
            raise  # Levanta a exceção para parar a execução do script

        # Dicionário para armazenar os últimos dados recebidos de cada robô/dispositivo
        self.dados_recebidos = {}
        self.rodando = True
        
        # A thread de leitura é essencial para não bloquear o programa principal
        self.thread_leitura = threading.Thread(target=self._ler_dados_serial)
        self.thread_leitura.daemon = True # Permite que o programa principal saia mesmo se a thread estiver rodando
        self.thread_leitura.start()

    def _ler_dados_serial(self):
        """
        Método executado em segundo plano pela thread para ler e processar dados.
        """
        while self.rodando:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    # Lê uma linha (até encontrar '\n'), decodifica de bytes para string
                    linha_bytes = self.ser.readline()
                    linha_str = linha_bytes.decode('utf-8').strip()
                    
                    # Remove caracteres nulos que podem vir de buffers em C
                    linha_str = linha_str.rstrip('\x00')

                    if not linha_str:
                        continue # Pula linhas vazias

                    print(f"Recebido: '{linha_str}'") # Debug: mostra o que foi recebido
                    
                    partes = linha_str.split(',')

                    # Validação do formato esperado: ID,dado1,dado2,...
                    # Exemplo do seu código anterior: ID,vel1,vel2,vel3,vel4,latencia (6 partes)
                    if len(partes) >= 2 and len(partes) % 6 == 0:
                        for i in range(0, len(partes), 6):
                            bloco = partes[i:i+6]
                            try:
                                id_robo = int(bloco[0])
                                velocidades = [float(v) for v in bloco[1:5]]
                                latencia = float(bloco[5])

                                # Armazena os dados no dicionário compartilhado
                                self.dados_recebidos[id_robo] = {
                                    'velocidades': velocidades,
                                    'latencia': latencia,
                                    'timestamp': time.time()
                                }
                            except (ValueError, IndexError):
                                print(f"  -> Aviso: Bloco de dados mal formatado: {bloco}")

                    else:
                        # Se o formato não for o esperado, apenas armazena a linha bruta
                        self.dados_recebidos['raw'] = linha_str

                except UnicodeDecodeError:
                    print(f"  -> Aviso: Erro de decodificação de bytes. Dados recebidos podem estar corrompidos.")
                except Exception as e:
                    print(f"  -> Erro inesperado na thread de leitura: {e}")
            
            time.sleep(0.01) # Pequena pausa para não sobrecarregar a CPU

    def enviar_comando(self, comando):
        """Envia uma string de comando para a porta serial."""
        if self.ser and self.ser.is_open:
            # Garante que o comando termina com uma quebra de linha
            if not comando.endswith('\n'):
                comando += '\n'
            
            try:
                self.ser.write(comando.encode('utf-8'))
                # print(f"Enviado: '{comando.strip()}'") # Descomente para debug de envio
            except serial.SerialException as e:
                print(f"ERRO ao enviar dados: {e}")

    def get_dados(self, id_robo):
        """Retorna os últimos dados recebidos para um ID específico."""
        return self.dados_recebidos.get(id_robo)

    def fechar(self):
        """Fecha a porta serial e termina a thread de forma segura."""
        print("Fechando a comunicação serial...")
        self.rodando = False
        self.thread_leitura.join() # Espera a thread terminar
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Porta serial fechada.")

# =============================================================================
#  EXEMPLO DE USO NO SCRIPT PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    # --- CONFIGURAÇÃO ---
    PORTA_SERIAL = "COM11" 
    BAUDRATE = 115200

    comunicador = None
    try:
        # 1. Inicializa e abre a comunicação
        comunicador = ComunicacaoSerial(PORTA_SERIAL, BAUDRATE)
        
        id_robo_alvo = 0
        contador = 0

        # 2. Loop principal da sua aplicação
        while True:
            # Monta um comando para enviar ao microcontrolador
            # Exemplo: "SET,ID,v1,v2,v3,v4"
            comando_para_enviar = f"SET,{id_robo_alvo},{contador},{contador+1},{contador-1},{contador*2}"
            
            # Envia o comando
            comunicador.enviar_comando(comando_para_enviar)
            
            # Recupera os últimos dados recebidos para o nosso robô alvo
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
            time.sleep(1) # Espera 1 segundo antes de repetir

    except serial.SerialException:
        # A exceção já foi tratada na classe, aqui apenas garantimos que o programa termine
        print("Programa encerrado devido a falha na porta serial.")
    except KeyboardInterrupt:
        # Permite que o usuário pare o programa com Ctrl+C
        print("\nPrograma interrompido pelo usuário.")
    finally:
        # 3. Garante que a porta serial seja sempre fechada ao sair
        if comunicador:
            comunicador.fechar()