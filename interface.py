import pygame
import time
from proto.actuator import Actuator

pygame.init()
pygame.joystick.init()
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

JOYSTICK_DEADZONE = 0.25
JOY_BUTTON_A = 0  # botão A do controle (Xbox-like)

screen_width, screen_height = 1200, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Controlador Manual - Red Dragons - 2025v1")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LIGHT_GRAY = (230, 230, 230)

font = pygame.font.Font(None, 60)
small_font = pygame.font.Font(None, 30)

robo_font = pygame.font.Font(None, 40)
robo0_text = robo_font.render("Robô 0", True, BLACK)
robo1_text = robo_font.render("Robô 1", True, BLACK)
robo2_text = robo_font.render("Robô 2", True, BLACK)

def draw_key(key, rect, pressed, intensity=None):
    # intensidade de 0..1 mistura GRAY->GREEN
    if intensity is None:
        color = GREEN if pressed else GRAY
    else:
        t = max(0.0, min(1.0, float(intensity)))
        color = (
            int(GRAY[0] + (GREEN[0] - GRAY[0]) * t),
            int(GRAY[1] + (GREEN[1] - GRAY[1]) * t),
            int(GRAY[2] + (GREEN[2] - GRAY[2]) * t),
        )
    pygame.draw.rect(screen, color, rect)
    text = font.render(key, True, BLACK)
    text_rect = text.get_rect(center=rect.center)
    screen.blit(text, text_rect)
    # barra de intensidade no rodapé da tecla, se houver
    if intensity is not None and intensity > 0:
        bar_margin = 6
        bar_height = 10
        bar_width = int((rect.width - 2 * bar_margin) * max(0.0, min(1.0, intensity)))
        bar_rect = pygame.Rect(rect.x + bar_margin, rect.bottom - bar_margin - bar_height, bar_width, bar_height)
        pygame.draw.rect(screen, BLACK, bar_rect, 0)

key_size = (80, 80)
keys = {
    "W": pygame.Rect(160, 75, *key_size),
    "A": pygame.Rect(80, 150, *key_size),
    "S": pygame.Rect(160, 150, *key_size),
    "D": pygame.Rect(240, 150, *key_size),
    "Q": pygame.Rect(80, 75, *key_size),
    "E": pygame.Rect(240, 75, *key_size),
    "X": pygame.Rect(160, 240, *key_size),

    "I": pygame.Rect(160+300, 75, *key_size),
    "J": pygame.Rect(80+300, 150, *key_size),
    "K": pygame.Rect(160+300, 150, *key_size),
    "L": pygame.Rect(240+300, 150, *key_size),
    "U": pygame.Rect(80+300, 75, *key_size),
    "O": pygame.Rect(240+300, 75, *key_size),
    "M": pygame.Rect(160+300, 240, *key_size),

    "5": pygame.Rect(160+600, 75, *key_size),
    "1": pygame.Rect(80+600, 150, *key_size),
    "2": pygame.Rect(160+600, 150, *key_size),
    "3": pygame.Rect(240+600, 150, *key_size),
    "4": pygame.Rect(80+600, 75, *key_size),
    "6": pygame.Rect(240+600, 75, *key_size),
    "0": pygame.Rect(160+600, 240, *key_size),
}

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
    "linear_0": "1",
    "angular_0": "5.0",
    "linear_1": "1",
    "angular_1": "5.0",
    "linear_2": "1",
    "angular_2": "5.0",
    "comm_port": "10330",
    "comm_ip": "localhost"
}

active_box = None
cursor_visible = True
last_cursor_toggle = time.time()

connected = False
button_rect = pygame.Rect(1000, 300, 150, 40)

def draw_input_box(name, rect, text, is_active):
    color = BLACK if is_active else LIGHT_GRAY
    pygame.draw.rect(screen, color, rect, 2)
    label = small_font.render(name, True, BLACK)
    screen.blit(label, (rect.x, rect.y - 30))
    text_surface = small_font.render(text, True, BLACK)
    screen.blit(text_surface, (rect.x + 5, rect.y + 5))
    if is_active:
        global cursor_visible, last_cursor_toggle
        if time.time() - last_cursor_toggle > 0.3:
            cursor_visible = not cursor_visible
            last_cursor_toggle = time.time()
        if cursor_visible:
            cursor_x = rect.x + 5 + text_surface.get_width()
            cursor_y = rect.y + 5
            cursor_height = text_surface.get_height()
            pygame.draw.line(screen, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)

def draw_button():
    pygame.draw.rect(screen, LIGHT_GRAY, button_rect)
    button_text = small_font.render("Conectar", True, BLACK)
    text_rect = button_text.get_rect(center=button_rect.center)
    screen.blit(button_text, text_rect)
    indicator_color = GREEN if connected else RED
    pygame.draw.circle(screen, indicator_color, (button_rect.left - 20, button_rect.centery), 10)

def verify_is_number(value):
    try:
        return float(value)
    except:
        return 0.0

def apply_deadzone(value, dz=JOYSTICK_DEADZONE, rescale=True):
    v = float(value)
    if abs(v) <= dz:
        return 0.0
    if not rescale:
        return v
    # reescala para usar todo o curso fora da deadzone ficando em [-1, 1]
    s = 1.0 if v > 0 else -1.0
    return s * (abs(v) - dz) / (1.0 - dz)

running = True
while running:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos):
                if not connected:
                    ip = imput_texts["comm_ip"]
                    port = int(imput_texts['comm_port'])
                    print("IP: ", ip)
                    print("Porta: ", port)
                    actuator = Actuator(ip=ip, team_port=port, logger=False)
                    connected = True
            else:
                for key, box in input_boxes.items():
                    if box.collidepoint(event.pos):
                        active_box = key
                        break
                else:
                    active_box = None
        elif event.type == pygame.KEYDOWN and active_box:
            if event.key == pygame.K_BACKSPACE:
                imput_texts[active_box] = imput_texts[active_box][:-1]
            elif event.key == pygame.K_RETURN:
                active_box = None
            else:
                imput_texts[active_box] += event.unicode

    screen.blit(robo0_text, (200 - robo0_text.get_width() // 2, 10))
    screen.blit(robo1_text, (500 - robo1_text.get_width() // 2, 10))
    screen.blit(robo2_text, (800 - robo2_text.get_width() // 2, 10))

    pressed_keys = pygame.key.get_pressed()
    draw_button()

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

    # inputs normalizados [-1..1] e velocidades
    in_fwd_0 = 0.0      # + frente, - trás (W/S)
    in_lat_0 = 0.0      # + esquerda, - direita (A/D)
    in_rot_0 = 0.0      # + anti-horário, - horário (Q/E)

    vx_0 = vy_0 = w_0 = 0.0
    vx_1 = vy_1 = w_1 = 0.0
    vx_2 = vy_2 = w_2 = 0.0
    kick_0 = kick_1 = kick_2 = 0

    # Joystick robô 0 (analógicos -> inputs proporcionais)
    joy_used = False
    joy_rot_used = False
    axis_x = axis_y = axis_rx = 0.0
    joy_btn_a = False
    if joystick:
        axis_x = joystick.get_axis(0)  # esquerdo X
        axis_y = joystick.get_axis(1)  # esquerdo Y
        if joystick.get_numaxes() > 3:
            axis_rx = joystick.get_axis(3)  # direito X
        if joystick.get_numbuttons() > JOY_BUTTON_A:
            joy_btn_a = bool(joystick.get_button(JOY_BUTTON_A))  # botão A -> chute

        in_lat_0 = -apply_deadzone(axis_x)   # A(+)/D(-)
        in_fwd_0 = -apply_deadzone(axis_y)   # W(+)/S(-) (Y invertido)
        joy_used = (abs(in_lat_0) > 0) or (abs(in_fwd_0) > 0)

        in_rot_0 = -apply_deadzone(axis_rx)  # Q(+)/E(-)
        joy_rot_used = abs(in_rot_0) > 0

    # Teclado robô 0 (fallback quando o analógico está parado)
    if not joy_used:
        if pressed_keys[pygame.K_w]: in_fwd_0 += 1.0
        if pressed_keys[pygame.K_s]: in_fwd_0 -= 1.0
        if pressed_keys[pygame.K_a]: in_lat_0 += 1.0
        if pressed_keys[pygame.K_d]: in_lat_0 -= 1.0
    if not joy_rot_used:
        if pressed_keys[pygame.K_q]: in_rot_0 += 1.0
        if pressed_keys[pygame.K_e]: in_rot_0 -= 1.0

    # clamp inputs para [-1, 1]
    in_fwd_0 = max(-1.0, min(1.0, in_fwd_0))
    in_lat_0 = max(-1.0, min(1.0, in_lat_0))
    in_rot_0 = max(-1.0, min(1.0, in_rot_0))

    # aplica velocidades
    vx_0 = in_fwd_0 * velocidade_linear_0
    vy_0 = in_lat_0 * velocidade_linear_0
    w_0  = in_rot_0 * velocidade_angular_0

    # chute: tecla X ou botão A do controle
    kick_active_0 = pressed_keys[pygame.K_x] or joy_btn_a
    if kick_active_0:
        kick_0 = 1

    # Intensidades para UI (0..1)
    inten_W = max(0.0, in_fwd_0)
    inten_S = max(0.0, -in_fwd_0)
    inten_A = max(0.0, in_lat_0)
    inten_D = max(0.0, -in_lat_0)
    inten_Q = max(0.0, in_rot_0)
    inten_E = max(0.0, -in_rot_0)

    # Desenhar teclas robô 0 com intensidade proporcional
    draw_key("W", keys["W"], inten_W > 0 or pressed_keys[pygame.K_w], intensity=inten_W)
    draw_key("A", keys["A"], inten_A > 0 or pressed_keys[pygame.K_a], intensity=inten_A)
    draw_key("S", keys["S"], inten_S > 0 or pressed_keys[pygame.K_s], intensity=inten_S)
    draw_key("D", keys["D"], inten_D > 0 or pressed_keys[pygame.K_d], intensity=inten_D)
    draw_key("Q", keys["Q"], inten_Q > 0 or pressed_keys[pygame.K_q], intensity=inten_Q)
    draw_key("E", keys["E"], inten_E > 0 or pressed_keys[pygame.K_e], intensity=inten_E)
    draw_key("X", keys["X"], kick_active_0)

    # Robô 1 (sem mudanças)
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

    # Robô 2 (sem mudanças)
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

    if active_box is None and connected:
        actuator.send_localVelocity_message(0, vx_0, vy_0, w_0, kick_0)
        actuator.send_localVelocity_message(1, vx_1, vy_1, w_1, kick_1)
        actuator.send_localVelocity_message(2, vx_2, vy_2, w_2, kick_2)

    pygame.display.flip()

pygame.quit()