# Comunicacao Software-Eletronica (Red Dragons SSL)

Repositório responsável pela comunicação UDP/Protobuf com o software de estratégia e transmissão via Serial para a placa de transmissão.

## Requisitos e Instalação

1. Python 3.10+
2. Instalar as dependências necessárias:
   ```bash
   pip install numpy pyserial pygame protobuf
   ```

## Como Usar

### 1. Interface de Teleoperação (`interface.py`)
Interface gráfica para controlar os robôs manualmente via teclado ou controle (Joystick/Xbox).

```bash
python3 interface.py
```
- Insira o **IP** e a **Porta** (ex: `10305` ou `10330`) e clique em **Conectar**.
- **Controles (Robô 0):** `W`, `A`, `S`, `D` (movimentação), `Q`, `E` (rotação) e `X` (chute) ou segundo o Joystick.

---

### 2. Receptor e Transmissor Principal (`main.py`)
Script principal que escuta as mensagens UDP de velocidade enviadas pela interface ou pela estratégia e repassa os pacotes serializados para a placa de transmissão via Serial.

```bash
python3 main.py
```

#### Principais Configurações (`main.py`):
- `NUM_ROBOTS`: Número de robôs (ex: `6` ou `3`).
- `RECEIVER_PORT`: Porta UDP de escuta dos pacotes protobuf (ex: `10305`).
- `SERIAL_FLAG`: `True` para enviar comandos via porta Serial (`/dev/ttyACM0`), ou `False` para apenas testar o recebimento via Socket.
- `SERIAL_PORT`: Caminho da porta USB conectada ao transmissor (ex: `/dev/ttyACM0`).
