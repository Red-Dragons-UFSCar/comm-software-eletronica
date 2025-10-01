import pygame
import time
from proto.actuator import Actuator

# Inicializar o Pygame
pygame.init()

# Configurações da tela
screen_width, screen_height = 1200, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Controlador Manual - Red Dragons - 2025v1")

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_GRAY = (230, 230, 230)

# Fonte
font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 30)

robo_font = pygame.font.Font(None, 40)  # Fonte para o título
robo0_text = robo_font.render("Robô 0", True, BLACK)  # Renderizar o título
robo1_text = robo_font.render("Robô 1", True, BLACK)  # Renderizar o título
robo2_text = robo_font.render("Robô 2", True, BLACK)  # Renderizar o título

# Função para desenhar a tecla
def draw_key(key, rect, pressed):
    color = GREEN if pressed else GRAY
    pygame.draw.rect(screen, color, rect)
    text = font.render(key, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    screen.blit(text, text_rect)

# Configurações das teclas (posição e tamanho)
key_size = (80, 80)
keys = {
    "W": pygame.Rect(160, 75, *key_size),
    "A": pygame.Rect(80, 150, *key_size),
    "S": pygame.Rect(160, 150, *key_size),
    "D": pygame.Rect(240, 150, *key_size),
    "Q": pygame.Rect(80, 75, *key_size),
    "E": pygame.Rect(240, 75, *key_size),
    "X": pygame.Rect(160, 240, *key_size),  # Chute robô 0

    "I": pygame.Rect(160+300, 75, *key_size),
    "J": pygame.Rect(80+300, 150, *key_size),
    "K": pygame.Rect(160+300, 150, *key_size),
    "L": pygame.Rect(240+300, 150, *key_size),
    "U": pygame.Rect(80+300, 75, *key_size),
    "O": pygame.Rect(240+300, 75, *key_size),
    "M": pygame.Rect(160+300, 240, *key_size),  # Chute robô 1

    "5": pygame.Rect(160+600, 75, *key_size),
    "1": pygame.Rect(80+600, 150, *key_size),
    "2": pygame.Rect(160+600, 150, *key_size),
    "3": pygame.Rect(240+600, 150, *key_size),
    "4": pygame.Rect(80+600, 75, *key_size),
    "6": pygame.Rect(240+600, 75, *key_size),
    "0": pygame.Rect(160+600, 240, *key_size),  # Chute robô 2
}

# Campos de texto para velocidade linear e angular
input_boxes = {
    "linear_0": pygame.Rect(100, 380, 100, 40),
    "angular_0": pygame.Rect(100, 480, 100, 40),
    "linear_1": pygame.Rect(100+300, 380, 100, 40),
    "angular_1": pygame.Rect(100+300, 480, 100, 40),
    "linear_2": pygame.Rect(100+600, 380, 100, 40),
    "angular_2": pygame.Rect(100+600, 480, 100, 40),
    "comm_port": pygame.Rect(1000, 200, 150, 40),
    "comm_ip": pygame.Rect(1000, 100, 150, 40)
}

imput_texts = {
    "linear_0": "", 
    "angular_0": "",
    "linear_1": "", 
    "angular_1": "",
    "linear_2": "", 
    "angular_2": "",
    "comm_port": "",
    "comm_ip": ""
}

active_box = None

cursor_visible = True
last_cursor_toggle = time.time()

connected = False  # Variável que indica o estado de conexão
button_rect = pygame.Rect(1000, 300, 150, 40)  # Posição e tamanho do botão "Conectar"

# Função para desenhar campo de texto
def draw_input_box(name, rect, text, is_active):
    color = BLACK if is_active else LIGHT_GRAY
    pygame.draw.rect(screen, color, rect, 2)
    label = small_font.render(name, True, BLACK)
    screen.blit(label, (rect.x, rect.y - 30))  # Colocar rótulo acima do campo
    text_surface = small_font.render(text, True, BLACK)
    screen.blit(text_surface, (rect.x + 5, rect.y + 5))

    # Desenhar o cursor se a caixa estiver ativa
    if is_active:
        # Alternar visibilidade do cursor
        global cursor_visible, last_cursor_toggle
        if time.time() - last_cursor_toggle > 0.3:  # Piscar o cursor a cada 0.5 segundos
            cursor_visible = not cursor_visible
            last_cursor_toggle = time.time()

        if cursor_visible:
            # Posição do cursor é após o texto atual
            cursor_x = rect.x + 5 + text_surface.get_width()
            cursor_y = rect.y + 5
            cursor_height = text_surface.get_height()
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)

def draw_button():
    pygame.draw.rect(screen, LIGHT_GRAY, button_rect)
    button_text = small_font.render("Conectar", True, BLACK)
    text_rect = button_text.get_rect(center=button_rect.center)
    screen.blit(button_text, text_rect)

    # Desenhar o indicador de conexão (um círculo)
    indicator_color = GREEN if connected else RED
    pygame.draw.circle(screen, indicator_color, (button_rect.left - 20, button_rect.centery), 10)


imput_texts["linear_0"] = "10"
imput_texts["angular_0"] = "50.0"
imput_texts["linear_1"] = "10"
imput_texts["angular_1"] = "50.0"
imput_texts["linear_2"] = "10"
imput_texts["angular_2"] = "50.0"
imput_texts["comm_port"] = "10330"
imput_texts["comm_ip"] = "localhost"

def verify_is_number(value):
    try:
        valor_convertido = float(value)
    except:
        valor_convertido = 0
    return valor_convertido

# Loop principal
running = True
while running:
    screen.fill(WHITE)

    # Verificar eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos):
                if not connected:
                    ip = imput_texts["comm_ip"]
                    port = int(imput_texts['comm_port'])

                    print("IP: ", ip)
                    print("Porta: ", port )
                    actuator = Actuator(ip=ip, team_port=port, logger=False)
                    connected = not connected  # Alternar o estado de conexão
            else:
                # Verificar se o clique foi em um campo de texto
                for key, box in input_boxes.items():
                    if box.collidepoint(event.pos):
                        active_box = key
                        break
                else:
                    active_box = None
        elif event.type == pygame.KEYDOWN:
            if active_box:
                if event.key == pygame.K_BACKSPACE:
                    imput_texts[active_box] = imput_texts[active_box][:-1]
                elif event.key == pygame.K_RETURN:
                    active_box = None
                else:
                    imput_texts[active_box] += event.unicode

    screen.blit(robo0_text, (200 - robo0_text.get_width() // 2, 10))  # Posicionar o título no centro
    screen.blit(robo1_text, (500 - robo0_text.get_width() // 2, 10))  # Posicionar o título no centro
    screen.blit(robo2_text, (800 - robo0_text.get_width() // 2, 10))  # Posicionar o título no centro

    # Verificar eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Verificar estado das teclas
    pressed_keys = pygame.key.get_pressed()

    # Desenhar o botão "Conectar" e o indicador de conexão
    draw_button()

    # Desenhar campos de texto para velocidades
    draw_input_box("Velocidade Linear", input_boxes["linear_0"], imput_texts["linear_0"], active_box == "linear_0")
    draw_input_box("Velocidade Angular", input_boxes["angular_0"], imput_texts["angular_0"], active_box == "angular_0")
    draw_input_box("Velocidade Linear", input_boxes["linear_1"], imput_texts["linear_1"], active_box == "linear_1")
    draw_input_box("Velocidade Angular", input_boxes["angular_1"], imput_texts["angular_1"], active_box == "angular_1")
    draw_input_box("Velocidade Linear", input_boxes["linear_2"], imput_texts["linear_2"], active_box == "linear_2")
    draw_input_box("Velocidade Angular", input_boxes["angular_2"], imput_texts["angular_2"], active_box == "angular_2")
    draw_input_box("Porta", input_boxes["comm_port"], imput_texts["comm_port"], active_box == "comm_port")
    draw_input_box("IP", input_boxes["comm_ip"], imput_texts["comm_ip"], active_box == "comm_ip")

    velocidade_linear_0 = verify_is_number(imput_texts["linear_0"])
    velocidade_angular_0 = verify_is_number(imput_texts["angular_0"])
    velocidade_linear_1 = verify_is_number(imput_texts["linear_1"])
    velocidade_angular_1 = verify_is_number(imput_texts["angular_1"])
    velocidade_linear_2 = verify_is_number(imput_texts["linear_2"])
    velocidade_angular_2 = verify_is_number(imput_texts["angular_2"])

    # print("Robo 0: ")
    # print("Velocidade Linear:", velocidade_linear_0)
    # print("Velocidade Angular:", velocidade_angular_0)
    # print("Robo 1: ")
    # print("Velocidade Linear:", velocidade_linear_1)
    # print("Velocidade Angular:", velocidade_angular_1)
    # print("Robo 2: ")
    # print("Velocidade Linear:", velocidade_linear_2)
    # print("Velocidade Angular:", velocidade_angular_2)

    vx_0, vy_0, w_0 = 0, 0, 0
    vx_1, vy_1, w_1 = 0, 0, 0
    vx_2, vy_2, w_2 = 0, 0, 0
    kick_0 = 0
    kick_1 = 0
    kick_2 = 0

    # Desenhar as teclas
    draw_key("W", keys["W"], pressed_keys[pygame.K_w])
    draw_key("A", keys["A"], pressed_keys[pygame.K_a])
    draw_key("S", keys["S"], pressed_keys[pygame.K_s])
    draw_key("D", keys["D"], pressed_keys[pygame.K_d])
    draw_key("Q", keys["Q"], pressed_keys[pygame.K_q])
    draw_key("E", keys["E"], pressed_keys[pygame.K_e])
    draw_key("X", keys["X"], pressed_keys[pygame.K_x])

    if pressed_keys[pygame.K_w]: vx_0 += velocidade_linear_0
    if pressed_keys[pygame.K_s]: vx_0 -= velocidade_linear_0
    if pressed_keys[pygame.K_a]: vy_0 += velocidade_linear_0
    if pressed_keys[pygame.K_d]: vy_0 -= velocidade_linear_0
    if pressed_keys[pygame.K_q]: w_0 += velocidade_angular_0
    if pressed_keys[pygame.K_e]: w_0 -= velocidade_angular_0
    if pressed_keys[pygame.K_x]: kick_0 = 1

    draw_key("I", keys["I"], pressed_keys[pygame.K_i])
    draw_key("J", keys["J"], pressed_keys[pygame.K_j])
    draw_key("K", keys["K"], pressed_keys[pygame.K_k])
    draw_key("L", keys["L"], pressed_keys[pygame.K_l])
    draw_key("U", keys["U"], pressed_keys[pygame.K_u])
    draw_key("O", keys["O"], pressed_keys[pygame.K_o])
    draw_key("M", keys["M"], pressed_keys[pygame.K_m])

    if pressed_keys[pygame.K_i]: vx_1 += velocidade_linear_1
    if pressed_keys[pygame.K_k]: vx_1 -= velocidade_linear_1
    if pressed_keys[pygame.K_j]: vy_1 += velocidade_linear_1
    if pressed_keys[pygame.K_l]: vy_1 -= velocidade_linear_1
    if pressed_keys[pygame.K_u]: w_1 += velocidade_angular_1
    if pressed_keys[pygame.K_o]: w_1 -= velocidade_angular_1
    if pressed_keys[pygame.K_m]: kick_1 = 1

    draw_key("5", keys["5"], pressed_keys[pygame.K_5] or pressed_keys[pygame.K_KP5])
    draw_key("1", keys["1"], pressed_keys[pygame.K_1] or pressed_keys[pygame.K_KP1])
    draw_key("2", keys["2"], pressed_keys[pygame.K_2] or pressed_keys[pygame.K_KP2])
    draw_key("3", keys["3"], pressed_keys[pygame.K_3] or pressed_keys[pygame.K_KP3])
    draw_key("4", keys["4"], pressed_keys[pygame.K_4] or pressed_keys[pygame.K_KP4])
    draw_key("6", keys["6"], pressed_keys[pygame.K_6] or pressed_keys[pygame.K_KP6])
    draw_key("0", keys["0"], pressed_keys[pygame.K_0] or pressed_keys[pygame.K_KP0])

    if pressed_keys[pygame.K_5] or pressed_keys[pygame.K_KP5]: vx_2 += velocidade_linear_2
    if pressed_keys[pygame.K_2] or pressed_keys[pygame.K_KP2]: vx_2 -= velocidade_linear_2
    if pressed_keys[pygame.K_1] or pressed_keys[pygame.K_KP1]: vy_2 += velocidade_linear_2
    if pressed_keys[pygame.K_3] or pressed_keys[pygame.K_KP3]: vy_2 -= velocidade_linear_2
    if pressed_keys[pygame.K_4] or pressed_keys[pygame.K_KP4]: w_2 += velocidade_angular_2
    if pressed_keys[pygame.K_6] or pressed_keys[pygame.K_KP6]: w_2 -= velocidade_angular_2
    if pressed_keys[pygame.K_0] or pressed_keys[pygame.K_KP0]: kick_2 = 1

    if active_box is None:
        if connected:
            actuator.send_localVelocity_message(0, vx_0, vy_0, w_0, kick_0)
            actuator.send_localVelocity_message(1, vx_1, vy_1, w_1, kick_1)
            actuator.send_localVelocity_message(2, vx_2, vy_2, w_2, kick_2)

    # Atualizar a tela
    pygame.display.flip()

# Finalizar o Pygame
pygame.quit()