import serial
import time


class UART:

    def __init__(self, port="/dev/serial0", baudrate=9600):

        self.port = port
        self.baudrate = baudrate
        self.ser = None

        self.conectar()


    def conectar(self):

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )

            print("==========================================================")
            print(" UART CONECTADO CON TIVA CORRECTAMENTE")
            print("==========================================================")

        except Exception as e:
            print(f"[ERROR UART] {e}")
            self.ser = None


    def enviar(self, mensaje):

        if self.ser is None:
            print("[UART] No hay conexión activa")
            return

        try:
            self.ser.write(mensaje.encode("utf-8"))
            time.sleep(0.05)

        except Exception as e:
            print(f"[UART ERROR ENVIO] {e}")



    def iniciar_juego(self, intentos):

        comando = f"S{intentos}\r\n"
        self.enviar(comando)

        print(f"[UART] Juego iniciado con {intentos} intentos")


    def correcto(self):

        self.enviar("r")
        print("[UART] Respuesta correcta enviada")


    def incorrecto(self):

        self.enviar("w")
        print("[UART] Respuesta incorrecta enviada")


    def cerrar(self):

        if self.ser:
            self.ser.close()
            print("[UART] Puerto cerrado correctamente")