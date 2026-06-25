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
    print("==========================================================")
    print(" Conexión UART3 establecida con éxito con la Tiva C")
    print("==========================================================")
    print("Instrucciones:")
    print("  - Escribe 'S' seguido de un número (ej. S5) para iniciar el juego.")
    print("  - Escribe 'r' para enviar un acierto rápido.")
    print("  - Escribe 'w' para enviar un fallo rápido.")
    print("  - Escribe 'salir' para cerrar el programa.")
    print("==========================================================\n")

except Exception as e:
    print(f"Error al abrir el puerto serial: {e}")
    print("Verifica que la UART esté activa en 'sudo raspi-config' y los cables bien puestos.")
    exit()

try:
    while True:
        # Captura lo que el usuario escribe en la terminal de la Raspberry Pi
        comando = input("Escribe el comando a enviar: ").strip()

        # Opción para salir del script de forma segura
        if comando.lower() == 'salir':
            print("Cerrando comunicación serial...")
            break

        # Validar que no se envíe una cadena vacía
        if not comando:
            continue

        # Si es el comando de inicio 'S', necesita el fin de línea (\r\n) para que el buffer de la Tiva lo detecte
        if comando.startswith('S') or comando.startswith('s'):
            # Convertimos a mayúscula por si acaso y agregamos el salto de línea
            mensaje_completo = comando.upper() + "\r\n"
            ser.write(mensaje_completo.encode('utf-8'))
            print(f"-> Enviado comando de inicio: {comando.upper()}")
        
        # Si es un comando rápido simple ('r' o 'w')
        else:
            ser.write(comando.encode('utf-8'))
            print(f"-> Enviado carácter: {comando}")

        # Un pequeño delay para no saturar el buffer y permitir que los hilos de la Pi respiren
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nPrograma interrumpido por el usuario (Ctrl+C).")

finally:
    # Asegura que el puerto siempre se cierre al terminar
    ser.close()
    print("Puerto serial cerrado correctamente.")