import random

OPERADORES = ["+", "-", "*", "/"]

def generar_operacion():

    while True:

        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operador = random.choice(OPERADORES)

        if operador == "/":

            num2 = random.randint(1, 20)
            num1 = num2 * random.randint(1, 10)

            resultado = num1 // num2

        else:

            expresion = f"{num1} {operador} {num2}"
            resultado = eval(expresion)

        if resultado < 0:
            continue

        return f"{num1} {operador} {num2}", resultado


def generar_lote(cantidad):

    return [generar_operacion() for _ in range(cantidad)]