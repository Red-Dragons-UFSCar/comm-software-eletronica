import time
import struct
import numpy as np
from communicators import Receiver, ComunicacaoSerial

CONV_RAD_HZ = 2*np.pi        # Conversão das velocidades para rad/s

RECEIVER_PORT = 10330       # Mesma porta que o código está mandando os comandos
CONTROL_FPS = 60        # Taxa de envio para o STM (Pode alterar aqui se necessário)

SERIAL_FLAG = False      # Habilita a comunicação por SERIAL (False para testar o SOCKET)
SERIAL_PORT = '/dev/ttyACM1'        # Conferir a USB utilizada
SERIAL_BAUD_RATE = 115200

# O código principal inverte os motores, coloque True para desinverter
MAIN_CODE = True

# ---------------------------------------------------------------------------------------------
#   INICIO DO CÓDIGO PRINCIPAL
# ---------------------------------------------------------------------------------------------

# Invertendo as velocidades
if MAIN_CODE:
    inverter = -1
else:
    inverter = 1

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
        inverter * int(robot0.wheel_velocity_front_left * CONV_RAD_HZ),
        inverter * int(robot0.wheel_velocity_front_right * CONV_RAD_HZ),
        inverter * int(robot0.wheel_velocity_back_right * CONV_RAD_HZ),
        inverter * int(robot0.wheel_velocity_back_left * CONV_RAD_HZ),
        kicker_bit(robot0),

        inverter * int(robot1.wheel_velocity_front_left * CONV_RAD_HZ),
        inverter * int(robot1.wheel_velocity_back_left * CONV_RAD_HZ),
        inverter * int(robot1.wheel_velocity_back_right * CONV_RAD_HZ),
        inverter * int(robot1.wheel_velocity_front_right * CONV_RAD_HZ),
        kicker_bit(robot1),

        inverter * int(robot2.wheel_velocity_front_left * CONV_RAD_HZ),
        inverter * int(robot2.wheel_velocity_back_left * CONV_RAD_HZ),
        inverter * int(robot2.wheel_velocity_back_right * CONV_RAD_HZ),
        inverter * int(robot2.wheel_velocity_front_right * CONV_RAD_HZ),
        kicker_bit(robot2),
    ]
    
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
