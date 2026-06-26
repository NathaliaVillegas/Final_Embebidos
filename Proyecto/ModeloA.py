import cv2
import numpy as np
from ultralytics import YOLO

# =========================================================
# 1. INICIALIZACIÓN GLOBAL (Se ejecuta una sola vez al importar)
# =========================================================
ruta_modelo = "runs/classify/runs/pizarra/clasificador_math_pro/weights/best.pt"
model = YOLO(ruta_modelo)

# Variables de estado para mantener la estabilidad entre frames
memoria_pizarra = {}
ID_CONTADOR = 0

# Constantes de la Región de Interés (ROI)
X_MIN_ROI, X_MAX_ROI = 20, 620
Y_MIN_ROI, Y_MAX_ROI = 20, 440

# =========================================================
# 2. FUNCIÓN PRINCIPAL DEL MÓDULO
# =========================================================
def detectar_numero(frame):
    """
    Recibe un frame de OpenCV, procesa los contornos, mantiene
    estabilidad temporal y devuelve la expresión matemática detectada.
    """
    global memoria_pizarra, ID_CONTADOR
    
    if frame is None:
        return ""

    # --- Preprocesamiento y Máscaras ---
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mascara_negro = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 85]))
    mascara_azul = cv2.inRange(hsv, np.array([90, 45, 30]), np.array([135, 255, 255]))
    mascara_rojo = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 50, 30]), np.array([12, 255, 255])),
        cv2.inRange(hsv, np.array([155, 50, 30]), np.array([180, 255, 255]))
    )
    mascara_total = cv2.bitwise_or(cv2.bitwise_or(mascara_negro, mascara_azul), mascara_rojo)

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

    # --- Detección de Contornos ---
    contornos, _ = cv2.findContours(mascara_limpia, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    casillas_actualizadas = set()

    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)
        
        # Filtros de tamaño y bordes
        if w > 12 and h > 6 and w < 110 and h < 110:
            if (x <= X_MIN_ROI + 12) or (x + w >= X_MAX_ROI - 12) or (y <= Y_MIN_ROI + 12) or (y + h >= Y_MAX_ROI - 5):
                continue

            centro_x = x + w // 2
            centro_y = y + h // 2
            
            # --- Lógica de Tracking ---
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
            
            # --- Inferencia con YOLO ---
            margen = 10
            recorte_raw = pizarra_perfecta[max(0, y-margen):min(frame.shape[0], y+h+margen), max(0, x-margen):min(frame.shape[1], x+w+margen)]

            if recorte_raw.size > 0:
                alto_r, ancho_r, _ = recorte_raw.shape
                max_dim = max(alto_r, ancho_r)
                recorte_cuadrado = np.ones((max_dim, max_dim, 3), dtype=np.uint8) * 255
                recorte_cuadrado[(max_dim-alto_r)//2 : (max_dim-alto_r)//2+alto_r, (max_dim-ancho_r)//2 : (max_dim-ancho_r)//2+ancho_r] = recorte_raw

                prediccion = model.predict(source=recorte_cuadrado, verbose=False, conf=0.35)
                
                if len(prediccion) > 0 and prediccion[0].probs is not None:
                    idx_ganador = prediccion[0].probs.top1
                    voto_actual = prediccion[0].names[idx_ganador]
                    datos_casilla["historial_votos"].append(voto_actual)

            # Estabilización a los 12 frames
            if datos_casilla["frames_visto"] >= 12:
                votos = datos_casilla["historial_votos"]
                if votos:
                    ganador = max(set(votos), key=votos.count)
                    
                    # Mapeo directo usando diccionario
                    diccionario_signos = {
                        "plus": "+", "minus": "-", "multiply": "X", 
                        "divide": "/", "equal": "=", "open_paren": "(", "close_paren": ")"
                    }
                    datos_casilla["char"] = diccionario_signos.get(ganador, ganador)

    # --- Limpieza de memoria (Objetos que desaparecieron) ---
    for id_reg in list(memoria_pizarra.keys()):
        if id_reg not in casillas_actualizadas:
            memoria_pizarra[id_reg]["frames_ausente"] += 1
            if memoria_pizarra[id_reg]["frames_ausente"] >= 15:
                del memoria_pizarra[id_reg]

    # --- Construcción de la cadena final ---
    elementos_validos = [datos for datos in memoria_pizarra.values() if datos["char"] is not None]
    elementos_ordenados = sorted(elementos_validos, key=lambda k: k["bbox"][0])
    expresion_completa = "".join([str(item["char"]) for item in elementos_ordenados])

    # Devolvemos el string (Ej: "5+2=7" o "12")
    return expresion_completa