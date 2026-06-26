from datetime import datetime
import os


class Historial:

    def __init__(self, nombre):

        self.nombre = nombre

        self.fecha = ""
        self.hora_inicio = ""
        self.hora_fin = ""

        self.modo = ""
        self.intentos = 0

        self.correctas = 0
        self.incorrectas = 0

        self.resultados = []

        os.makedirs("recursos", exist_ok=True)

        self.archivo = os.path.join(
            "recursos",
            "usuarios.txt"
        )


    def iniciar_sesion(self, modo, intentos):

        ahora = datetime.now()

        self.fecha = ahora.strftime("%d/%m/%Y")
        self.hora_inicio = ahora.strftime("%H:%M:%S")

        self.modo = modo
        self.intentos = intentos


    def agregar_resultado(
        self,
        ejercicio,
        respuesta,
        correcta
    ):

        self.resultados.append({
            "ejercicio": ejercicio,
            "respuesta": respuesta,
            "correcta": correcta
        })

        if correcta:
            self.correctas += 1
        else:
            self.incorrectas += 1


    def puntaje(self):

        total = self.correctas + self.incorrectas

        if total == 0:
            return 0

        return round((self.correctas / total) * 100, 2)


    def finalizar_sesion(self):

        ahora = datetime.now()
        self.hora_fin = ahora.strftime("%H:%M:%S")

        with open(self.archivo, "a", encoding="utf-8") as archivo:

            archivo.write("=" * 70 + "\n")

            archivo.write(f"USUARIO: {self.nombre}\n")
            archivo.write(f"FECHA: {self.fecha}\n")
            archivo.write(f"HORA DE INICIO: {self.hora_inicio}\n")
            archivo.write(f"HORA DE FIN: {self.hora_fin}\n\n")

            archivo.write(f"MODO: {self.modo}\n")
            archivo.write(f"INTENTOS: {self.intentos}\n\n")

            archivo.write("RESULTADOS\n\n")

            for i, resultado in enumerate(self.resultados, start=1):

                estado = "Correcto" if resultado["correcta"] else "Incorrecto"

                archivo.write(
                    f"{i}) "
                    f"{resultado['ejercicio']}    "
                    f"Respuesta: {resultado['respuesta']}    "
                    f"-> {estado}\n"
                )

            archivo.write("\n")

            archivo.write(f"Correctas   : {self.correctas}\n")
            archivo.write(f"Incorrectas : {self.incorrectas}\n")
            archivo.write(f"Puntaje     : {self.puntaje()}%\n")

            archivo.write("\n")
            archivo.write("=" * 70)
            archivo.write("\n\n")