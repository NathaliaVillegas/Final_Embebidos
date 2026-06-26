import cv2
import numpy as np
from ultralytics import YOLO

# 1. Cargar el modelo de clasificación entrenado
ruta_modelo = "runs/classify/runs/pizarra/clasificador_math_pro/weights/best.pt"
model = YOLO(ruta_modelo)

# 2. Inicializar la webcam USB
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("====================================================")
print("  MOTOR NATIVO PURIFICADO - CONFIDENZA 100% EN YOLO")
print("  PRESIONA 'E' PARA EVALUAR LA ECUACIÓN EN TERMINAL")
print("  PRESIONA 'Q' PARA SALIR")
print("====================================================")

cv2.namedWindow("Deteccion Optimizada", cv2.WINDOW_NORMAL)

# ESTRUCTURAS DE MEMORIA TEMPORAL AUTÓNOMA (Previene parpadeos)
memoria_pizarra = {}
ID_CONTADOR = 0

# REGION DE INTERÉS (ROI) TOTALMENTE CONFIGURADA
X_MIN_ROI, X_MAX_ROI = 20, 620
Y_MIN_ROI, Y_MAX_ROI = 20, 440

def evaluar_pizarra():
    global memoria_pizarra
    elementos_validos = [datos for datos in memoria_pizarra.values() if datos["char"] is not None]
    
    if not elementos_validos:
        print("[EVALUADOR] Pizarra vacía.")
        return

    # Ordenamiento espacial robusto de izquierda a derecha (Eje X)
    elementos_ordenados = sorted(elementos_validos, key=lambda k: k["bbox"][0])
    expresion_completa = "".join([str(item["char"]) for item in elementos_ordenados])
    print(f"\n[EVALUADOR] Cadena leída: {expresion_completa}")

    if "=" not in expresion_completa:
        print("[EVALUADOR] Falta el signo '=' para procesar la igualdad.")
        return

    try:
        partes = expresion_completa.split("=")
        miembro_izq = partes[0]
        resultado_propuesto_str = partes[1]

        if not miembro_izq or not resultado_propuesto_str:
            print("[EVALUADOR] Estructura incompleta.")
            return

        ecuacion_limpia = miembro_izq.replace("X", "*").replace("x", "*")
        valor_real = eval(ecuacion_limpia)
        valor_propuesto = float(resultado_propuesto_str)

        print(f"[ANALIZADOR] {miembro_izq} = {valor_propuesto} | Resultado Real: {valor_real}")

        if abs(valor_real - valor_propuesto) < 0.001:
            print("=========================================")
            print("       ¡RESULTADO 100% CORRECTO! 🍬      ")
            print("=========================================")
        else:
            print("=========================================")
            print("       RESULTADO INCORRECTO ❌           ")
            print("=========================================")

    except Exception as e:
        print(f"[ERROR PARSER] No se pudo calcular: {e}")

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    imagen_visual = frame.copy()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Máscaras HSV estables
    mascara_negro = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 85]))
    mascara_azul = cv2.inRange(hsv, np.array([90, 45, 30]), np.array([135, 255, 255]))
    mascara_rojo = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 50, 30]), np.array([12, 255, 255])),
        cv2.inRange(hsv, np.array([155, 50, 30]), np.array([180, 255, 255]))
    )
    mascara_total = cv2.bitwise_or(cv2.bitwise_or(mascara_negro, mascara_azul), mascara_rojo)

    # Filtro ROI
    mascara_roi = np.zeros_like(mascara_total)
    mascara_roi[Y_MIN_ROI:Y_MAX_ROI, X_MIN_ROI:X_MAX_ROI] = 255
    mascara_limpia = cv2.bitwise_and(mascara_total, mascara_roi)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_CLOSE, kernel, iterations=1)

    pizarra_perfecta = cv2.bitwise_or(
        cv2.bitwise_and(frame, frame, mask=mascara_limpia),
        cv2.bitwise_and(np.ones_like(frame)*255, np.ones_like(frame)*255, mask=cv2.bitwise_not(mascara_limpia))
    )

    contornos, _ = cv2.findContours(mascara_limpia, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    casillas_actualizadas = set()

    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)
        
        # Filtro de tamaño mínimo base
        if w > 12 and h > 6 and w < 110 and h < 110:
            # Filtro anti-bordes de madera
            if (x <= X_MIN_ROI + 12) or (x + w >= X_MAX_ROI - 12) or (y <= Y_MIN_ROI + 12) or (y + h >= Y_MAX_ROI - 5):
                continue

            centro_x = x + w // 2
            centro_y = y + h // 2
            
            id_asociado = None
            for id_reg, datos in memoria_pizarra.items():
                bx, by, bw, bh = datos["bbox"]
                if abs(centro_x - (bx + bw // 2)) < 25 and abs(centro_y - (by + bh // 2)) < 25:
                    id_asociado = id_reg
                    break
            
            if id_asociado is None:
                id_asociado = ID_CONTADOR
                memoria_pizarra[id_asociado] = {"char": None, "bbox": (x, y, w, h), "frames_visto": 0, "historial_votos": [], "frames_ausente": 0}
                ID_CONTADOR += 1
            
            casillas_actualizadas.add(id_asociado)
            datos_casilla = memoria_pizarra[id_asociado]
            datos_casilla["frames_ausente"] = 0
            datos_casilla["bbox"] = (x, y, w, h)

            if datos_casilla["char"] is not None:
                continue

            datos_casilla["frames_visto"] += 1
            
            margen = 10
            recorte_raw = pizarra_perfecta[max(0, y-margen):min(frame.shape[0], y+h+margen), max(0, x-margen):min(frame.shape[1], x+w+margen)]

            if recorte_raw.size > 0:
                alto_r, ancho_r, _ = recorte_raw.shape
                max_dim = max(alto_r, ancho_r)
                recorte_cuadrado = np.ones((max_dim, max_dim, 3), dtype=np.uint8) * 255
                recorte_cuadrado[(max_dim-alto_r)//2 : (max_dim-alto_r)//2+alto_r, (max_dim-ancho_r)//2 : (max_dim-ancho_r)//2+ancho_r] = recorte_raw

                # Inferencia con un umbral de confianza estándar estable (0.35)
                prediccion = model.predict(source=recorte_cuadrado, verbose=False, conf=0.35)
                
                if len(prediccion) > 0 and prediccion[0].probs is not None:
                    idx_ganador = prediccion[0].probs.top1
                    voto_actual = prediccion[0].names[idx_ganador]

                    # Metemos el voto directo del modelo al historial de estabilidad temporal
                    datos_casilla["historial_votos"].append(voto_actual)

            # Consenso de estabilidad tras 12 frames continuos
            if datos_casilla["frames_visto"] >= 12:
                votos = datos_casilla["historial_votos"]
                if votos:
                    ganador = max(set(votos), key=votos.count)
                    
                    # Mapeo semántico limpio
                    if ganador == "plus": ganador = "+"
                    elif ganador == "minus": ganador = "-"
                    elif ganador == "multiply": ganador = "X"
                    elif ganador == "divide": ganador = "/"
                    elif ganador == "equal": ganador = "="
                    elif ganador == "open_paren": ganador = "("
                    elif ganador == "close_paren": ganador = ")"
                    
                    datos_casilla["char"] = ganador

    # Auto-borrado temporal por ausencia de píxeles
    for id_reg in list(memoria_pizarra.keys()):
        if id_reg not in casillas_actualizadas:
            memoria_pizarra[id_reg]["frames_ausente"] += 1
            if memoria_pizarra[id_reg]["frames_ausente"] >= 15:
                del memoria_pizarra[id_reg]

    # Capa gráfica estable
    for id_reg, datos in memoria_pizarra.items():
        if datos["char"] is not None:
            bx, by, bw, bh = datos["bbox"]
            cv2.rectangle(imagen_visual, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv2.putText(imagen_visual, datos["char"], (bx, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Dibujar recuadro guía azul
    cv2.rectangle(imagen_visual, (X_MIN_ROI, Y_MIN_ROI), (X_MAX_ROI, Y_MAX_ROI), (255, 0, 0), 1)
    cv2.imshow("Deteccion Optimizada", imagen_visual)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('e'):
        evaluar_pizarra()

cap.release()
cv2.destroyAllWindows()
print("[INFO] Proceso finalizado.")