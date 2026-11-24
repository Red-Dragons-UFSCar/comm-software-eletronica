import glob
import time
import struct
import numpy as np
from communicators import Receiver, ComunicacaoSerial

CONV_RAD_HZ = 2*np.pi        # Conversão das velocidades para rad/s

RECEIVER_PORT = 10315      # Mesma porta que o código está mandando os comandos
CONTROL_FPS = 60        # Taxa de envio para o STM (Pode alterar aqui se necessário)

SERIAL_FLAG = True      # Habilita a comunicação por SERIAL (False para testar o SOCKET)
_stm_ports = glob.glob('/dev/serial/by-id/*STM32_Virtual_ComPort*')
SERIAL_PORT = _stm_ports[0] if _stm_ports else '/dev/ttyACM1'        # Conferir a USB utilizada
SERIAL_BAUD_RATE = 115200

# O código principal inverte os motores, coloque True para desinverter
MAIN_CODE = False

# O transmissor só tem 3 posições (0, 1 e 2). Aqui você diz qual id do software
# vai em cada posição: {id_no_software: posição}. Ex.: {0: 0, 3: 1, 5: 2}.
# IDs que não estiverem aqui são ignorados (aparece um aviso no terminal).
MAPA_IDS = {0: 0, 1: 1, 2: 2}

# Mapeamento das rodas para os acionamentos: posição i -> conector SELM(i+1) do robô.
# ORDEM: qual roda do software vai em cada posição ('fl', 'bl', 'br', 'fr')
# SINAL: +1 ou -1 por posição (multiplicado também por `inverter`)
# Montagem atual (cabos dos dois acionamentos da frente trocados entre si):
#   SELM1 = traseira esquerda, SELM2 = dianteira direita,
#   SELM3 = dianteira esquerda, SELM4 = traseira direita.
# O positivo dos motores é horário e o da cinemática (RedSSL, phi 55/125/235/305) é anti-horário,
# por isso todos os sinais são -1.
ORDEM = ['bl', 'fr', 'fl', 'br']
SINAL = [-1, -1, -1, -1]

# ---------------------------------------------------------------------------------------------
#   INICIO DO CÓDIGO PRINCIPAL
# ---------------------------------------------------------------------------------------------

# Invertendo as velocidades
if MAIN_CODE:
    inverter = -1
else:
    inverter = 1

# Inicialização do recebimento das mensagens via socket
receiver = Receiver(port=RECEIVER_PORT, logger=False, mapa_ids=MAPA_IDS)
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

    # Robô 2 é o atacante no software, mas Robô 0 para eletrônica
    # ...
    
    # Ordem e sinal de cada posição vêm de ORDEM/SINAL (topo do arquivo).
    # Posição i da lista -> conector SELM(i+1) do robô.
    def rodas(r):
        vel = {
            'fl': r.wheel_velocity_front_left,
            'bl': r.wheel_velocity_back_left,
            'br': r.wheel_velocity_back_right,
            'fr': r.wheel_velocity_front_right,
        }
        return [inverter * SINAL[i] * int(vel[ORDEM[i]] * CONV_RAD_HZ)
                for i in range(4)] + [kicker_bit(r)]

    valores_para_enviar = rodas(robot2) + rodas(robot1) + rodas(robot0)
    
    print(f"[DEBUG] Lista enviada: {valores_para_enviar}\n")

    formato = f'<{len(valores_para_enviar)}i'  # 15 inteiros
    comando_em_bytes = struct.pack(formato, *valores_para_enviar)
    
    if comunicador:
    
        # Envia o comando em formato de bytes
        comunicador.enviar_comando(comando_em_bytes)
        
        # Valores recebidos da eletrônica
        id_robo_alvo = 1
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
