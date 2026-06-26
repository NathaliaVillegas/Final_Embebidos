import serial
import time

# Configura el puerto serial en los pines GPIO 14 y 15 de la Raspberry Pi
try:
    ser = serial.Serial(
        port='/dev/serial0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    
    print(" Conexión UART3 establecida")


except Exception as e:
    print(f"Error al abrir el puerto serial: {e}")
    print("Verifica que la UART esté activa en 'sudo raspi-config' y los cables bien puestos.")
    exit()

try:
    while True:
        
        comando = input("Escribe el comando a enviar: ").strip()
        if comando.lower() == 'salir':
            print("Cerrando comunicación serial...")
            break

        if not comando:
            continue

        if comando.startswith('S') or comando.startswith('s'):
            mensaje_completo = comando.upper() + "\r\n"
            ser.write(mensaje_completo.encode('utf-8'))
            print(f"-> Enviado comando de inicio: {comando.upper()}")
        
        else:
            ser.write(comando.encode('utf-8'))
            print(f"-> Enviado carácter: {comando}")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nPrograma interrumpido por el usuario (Ctrl+C).")

finally:
    ser.close()
    print("Puerto serial cerrado correctamente.")