import time
import socket
import threading
import struct
import serial
import numpy as np
from proto.ssl_simulation_robot_control_pb2 import RobotControl

CONV_GEAR = 1.25
CONV_RAD_HZ = 1/(2*np.pi)

RECEIVER_FPS = 3000  # Taxa de aquisição da rede dos pacotes do software
RECEIVER_PORT = 10330   # Mesma porta que o código está mandando os comandos
CONTROL_FPS = 60  # Taxa de envio para o STM (Pode alterar aqui se necessário)

SERIAL_FLAG = True # Habilita a comunicação por SERIAL (False para testar o SOCKET)
SERIAL_PORT = '/dev/ttyACM1' # Conferir a USB utilizada
SERIAL_BAUD_RATE = 115200

# ---------------------------------------------------------------------------------------------
#    DEFINIÇÃO DE CLASSES
# ---------------------------------------------------------------------------------------------

class RepeatTimer(threading.Timer):
    """
    Descrição:
        Classe herdada de Timer para execução paralela da thread de recebimento das velocidades
    """
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class RobotVelocity:
    """
    Descrição:
        Classe para armazenar as velocidades de cada robô
    Entradas:
        id_robot:   Robô que corresponde às velocidades do objeto (0 a 2)
    """
    def __init__(self, id_robot):
        self.id_robot = id_robot  # id do robô
        # Velocidades angulares
        self.wheel_velocity_front_right = 0 
        self.wheel_velocity_back_right = 0
        self.wheel_velocity_back_left = 0
        self.wheel_velocity_front_left = 0
        self.kick_speed = 0

        self.cont_not_message = 0
        self.treshold_message = 2*RECEIVER_FPS

class Receiver():
    def __init__(self, ip: str = 'localhost', port: int = 10330, logger: bool = False):
        """
        Descrição:
            Classe para recepção de mensagens serializadas usando Google Protobuf.
        
        Entradas:
            ip:       Endereço IP para escuta. Padrão é 'localhost'.
            port:     Porta de escuta. Padrão é 10302.
            logger:   Flag que ativa o log de recebimento de mensagens no terminal.
        """
        # Parâmetros de rede
        self.ip = ip
        self.port = port
        self.buffer_size = 65536  # Tamanho máximo do buffer para receber mensagens

        # Controle de log
        self.logger = logger

        # Robôs a serem controlados
        self.robot0 = RobotVelocity(0)
        self.robot1 = RobotVelocity(1)
        self.robot2 = RobotVelocity(2)
        self.robots = [self.robot0, self.robot1, self.robot2]

        # Criar socket
        self._create_socket()

    def _create_socket(self):
        """Cria e configura o socket UDP."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Adicionado para permitir que múltiplos sockets se conectem à mesma porta.
        # Funciona em sistemas baseados em Linux/Unix, pode não estar disponível no Windows.
        if hasattr(socket, 'SO_REUSEPORT'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self.socket.bind((self.ip, self.port))
        self.socket.settimeout(0.1) # Timeout para não bloquear indefinidamente

    def receive_socket(self):
        """
        Descrição:
            Método responsável por receber a mensagem serializada e desserializá-la usando o Protobuf.
        
        Retorna:
            Instância da classe Protobuf desserializada ou None se não receber nada.
        """
        try:
            data, _ = self.socket.recvfrom(self.buffer_size)
            if self.logger:
                print("[Receiver] Mensagem recebida")

            # Desserializar a mensagem usando a classe Protobuf RobotControl
            message = RobotControl()
            message.ParseFromString(data)
            self.decode_message(message)

        except socket.error as e:
            if e.errno == socket.errno.EAGAIN:
                # Nenhuma mensagem disponível no momento
                # Se ficar muito tempo sem receber mensagens, a velocidade do robô vai a zero
                for robot in self.robots:
                    if robot.cont_not_message > robot.treshold_message:
                        robot.wheel_velocity_front_right = 0
                        robot.wheel_velocity_back_right = 0
                        robot.wheel_velocity_back_left = 0
                        robot.wheel_velocity_front_left = 0
                    else:
                        robot.cont_not_message += 1
                
                return None
            else:
                print("[Receiver] Erro de socket:", e)
                return None
            
    def decode_message(self, message):
        id_robot = message.robot_commands[0].id
        wheel_velocity_front_right = message.robot_commands[0].move_command.wheel_velocity.front_right
        wheel_velocity_back_right = message.robot_commands[0].move_command.wheel_velocity.back_right
        wheel_velocity_back_left = message.robot_commands[0].move_command.wheel_velocity.back_left
        wheel_velocity_front_left = message.robot_commands[0].move_command.wheel_velocity.front_left
        kick_speed = message.robot_commands[0].kick_speed
        self.robots[id_robot].wheel_velocity_front_right = wheel_velocity_front_right
        self.robots[id_robot].wheel_velocity_back_right = wheel_velocity_back_right
        self.robots[id_robot].wheel_velocity_back_left = wheel_velocity_back_left
        self.robots[id_robot].wheel_velocity_front_left = wheel_velocity_front_left
        self.robots[id_robot].cont_not_message = 0
        self.robots[id_robot].kick_speed = kick_speed

            
    def start_thread(self):
        """
        Descrição:
            Função que inicia a thread da visão
        """
        self.vision_thread = RepeatTimer((1 / RECEIVER_FPS), self.receive_socket)
        self.vision_thread.start()
        
class ComunicacaoSerial:
    def __init__(self, porta, baudrate=115200, timeout=1):
        """
        Descrição:
            Classe para recepção e envio de mensagens para o transmissor via SERIAL.
        
        Entradas:
            porta
            baudrate
            timeout
        """
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

                    # print(f"[DEBUG] Recebido: '{linha_str}'")
                    
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

    def enviar_comando(self, comando):
        """
        Método que envia uma string de comando ou um objeto de bytes para a porta serial.
        """
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
                # print(f"[DEBUG] Enviado: {dados_para_enviar}")
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
    
    def decode_message(self, message):
        id_robot = message.robot_commands[0].id
        wheel_velocity_front_right = message.robot_commands[0].move_command.wheel_velocity.front_right
        wheel_velocity_back_right = message.robot_commands[0].move_command.wheel_velocity.back_right
        wheel_velocity_back_left = message.robot_commands[0].move_command.wheel_velocity.back_left
        wheel_velocity_front_left = message.robot_commands[0].move_command.wheel_velocity.front_left
        kick_speed = message.robot_commands[0].kick_speed
        self.robots[id_robot].wheel_velocity_front_right = wheel_velocity_front_right
        self.robots[id_robot].wheel_velocity_back_right = wheel_velocity_back_right
        self.robots[id_robot].wheel_velocity_back_left = wheel_velocity_back_left
        self.robots[id_robot].wheel_velocity_front_left = wheel_velocity_front_left
        self.robots[id_robot].cont_not_message = 0
        self.robots[id_robot].kick_speed = kick_speed

# ---------------------------------------------------------------------------------------------
#   INICIO DO CÓDIGO PRINCIPAL
# ---------------------------------------------------------------------------------------------

# Inicialização do recebimento das mensagens via socket
receiver = Receiver(port=RECEIVER_PORT, logger=False)
receiver.start_thread()

# Inicialização do objeto serial
comunicador = None
if SERIAL_FLAG:
    comunicador = ComunicacaoSerial(SERIAL_PORT, SERIAL_BAUD_RATE)

while True:
    t1 = time.time()

    receiver.receive_socket()
    # Acesso das variáveis obtidas pela rede em cada um dos robôs [0, 1 e 2]
    for robot in receiver.robots:
        print("Robô ", robot.id_robot)
        print("Frente direita: ", robot.wheel_velocity_front_right)
        print("Frente esquerda: ", robot.wheel_velocity_front_left)
        print("Trás direita: ", robot.wheel_velocity_back_right)
        print("Trás esquerda: ", robot.wheel_velocity_back_left)
        print(f"Kick speed: {robot.kick_speed}\n")

    # Caso a interface com o teclado não esteja pronta ainda, descomente as linhas abaixo
    # Elas possuem casos padrão para testes básicos de validação.

    # Robô 0 a 0.5m/s pra frente - descomentar as próximas 5 linhas
    robot0 = receiver.robots[0]
    #robot0.wheel_velocity_front_right = 0
    #robot0.wheel_velocity_front_left = 0
    # robot0.wheel_velocity_back_right = 0
    #robot0.wheel_velocity_back_left = 0

    # Robô 1 a 0.5m/s pra cima - descomentar as próximas 5 linhas
    robot1 = receiver.robots[1]
    # robot1.wheel_velocity_front_right = 9.25926
    # robot1.wheel_velocity_front_left = 9.259256
    # robot1.wheel_velocity_back_right = -13.09457
    # robot1.wheel_velocity_back_left = -13.09457

    # Robô 2 a 1 rad/s (apenas girando) - descomentar as próximas 5 linhas
    robot2 = receiver.robots[2]
    # robot2.wheel_velocity_front_right = -16.03751
    # robot2.wheel_velocity_front_left = 16.03751
    # robot2.wheel_velocity_back_right = -13.09457
    # robot2.wheel_velocity_back_left = -13.09457

    # Mensagem a ser enviada - Padrão 1
    # Velocidades das rodas  (1,2,3,4) dos robos (1,2,3) (Roda 1 robo1, Roda 2 robo 1, Roda 3 Robo 1 ... )
    # Padrão software: (1,2,3,4)
    # Padrão Eletrônica: (4,3,2,1)
    
    def kicker_bit(r): # Se o kicker estiver ativo, retorna 1, senão 0
        return 1 if getattr(r, 'kick_speed', 0) != 0 else 0

    valores_para_enviar = [
        int(robot0.wheel_velocity_front_left),
        int(robot0.wheel_velocity_back_left),
        int(robot0.wheel_velocity_back_right),
        int(robot0.wheel_velocity_front_right),
        kicker_bit(robot0),

        int(robot1.wheel_velocity_front_left),
        int(robot1.wheel_velocity_back_left),
        int(robot1.wheel_velocity_back_right),
        int(robot1.wheel_velocity_front_right),
        kicker_bit(robot1),

        int(robot2.wheel_velocity_front_left),
        int(robot2.wheel_velocity_back_left),
        int(robot2.wheel_velocity_back_right),
        int(robot2.wheel_velocity_front_right),
        kicker_bit(robot2),
    ]
    
    # print(f"[DEBUG] Lista enviada: {valores_para_enviar}\n")

    formato = f'<{len(valores_para_enviar)}i'  # 15 inteiros
    comando_em_bytes = struct.pack(formato, *valores_para_enviar)
    
    if comunicador:
    
        # Envia o comando em formato de bytes
        comunicador.enviar_comando(comando_em_bytes)
        
        # Valores recebidos da eletrônica
        id_robo_alvo = 0
        dados_atuais = comunicador.get_dados(id_robo_alvo)
                
        print("-" * 30)
        if dados_atuais:
            print(f"Últimos dados recebidos do Robô {id_robo_alvo}:")
            print(f"  - Velocidades: {dados_atuais['velocidades']}")
            print(f"  - Latência: {dados_atuais['latencia']:.4f} s")
            print(f"  - Recebido há: {time.time() - dados_atuais['timestamp']:.2f} s")
        else:
            print(f"Aguardando dados do Robô {id_robo_alvo}...")

    t2 = time.time()

    if (1/CONTROL_FPS - (t2-t1) > 0):
        time.sleep(1/CONTROL_FPS - (t2-t1))
