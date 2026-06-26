from operaciones import generar_lote


operaciones = generar_lote(10)

print("        GENERADOR DE OPERACIONES MATEMÁTICAS        ")

for i, (expr, res) in enumerate(operaciones, start=1):

    print(f"Pregunta {i}: {expr} = {res}")
