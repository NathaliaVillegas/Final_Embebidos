import cv2
import numpy as np
from ultralytics import YOLO

# =========================================================
# MODELO
# =========================================================
ruta_modelo = "runs/classify/runs/pizarra/clasificador_math_pro/weights/best.pt"
model = YOLO(ruta_modelo)

# =========================================================
# MEMORIA GLOBAL
# =========================================================
memoria_pizarra = {}
ID_CONTADOR = 0

X_MIN_ROI, X_MAX_ROI = 20, 620
Y_MIN_ROI, Y_MAX_ROI = 20, 440


# =========================================================
# FUNCIÓN USABLE DESDE MAIN / TKINTER
# =========================================================
def detectar_numero(frame):
    global memoria_pizarra, ID_CONTADOR

    if frame is None:
        return ""

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mascara_negro = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 85]))
    mascara_azul = cv2.inRange(hsv, np.array([90, 45, 30]), np.array([135, 255, 255]))
    mascara_rojo = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 50, 30]), np.array([12, 255, 255])),
        cv2.inRange(hsv, np.array([155, 50, 30]), np.array([180, 255, 255]))
    )

    mascara_total = cv2.bitwise_or(mascara_negro, mascara_azul)
    mascara_total = cv2.bitwise_or(mascara_total, mascara_rojo)

    mascara_roi = np.zeros_like(mascara_total)
    mascara_roi[Y_MIN_ROI:Y_MAX_ROI, X_MIN_ROI:X_MAX_ROI] = 255

    mascara_limpia = cv2.bitwise_and(mascara_total, mascara_roi)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_CLOSE, kernel, iterations=1)

    pizarra_perfecta = cv2.bitwise_or(
        cv2.bitwise_and(frame, frame, mask=mascara_limpia),
        cv2.bitwise_and(np.ones_like(frame) * 255, np.ones_like(frame) * 255, mask=cv2.bitwise_not(mascara_limpia))
    )

    contornos, _ = cv2.findContours(mascara_limpia, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    casillas_actualizadas = set()

    for c in contornos:

        x, y, w, h = cv2.boundingRect(c)

        if not (12 < w < 110 and 6 < h < 110):
            continue

        if (x <= X_MIN_ROI + 12 or x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or y + h >= Y_MAX_ROI - 5):
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
            memoria_pizarra[id_asociado] = {
                "char": None,
                "bbox": (x, y, w, h),
                "frames_visto": 0,
                "historial_votos": [],
                "frames_ausente": 0
            }
            ID_CONTADOR += 1

        casillas_actualizadas.add(id_asociado)
        datos = memoria_pizarra[id_asociado]

        datos["bbox"] = (x, y, w, h)
        datos["frames_ausente"] = 0

        if datos["char"] is not None:
            continue

        datos["frames_visto"] += 1

        margen = 10
        recorte = pizarra_perfecta[
            max(0, y-margen):min(frame.shape[0], y+h+margen),
            max(0, x-margen):min(frame.shape[1], x+w+margen)
        ]

        if recorte.size > 0:
            h2, w2, _ = recorte.shape
            max_dim = max(h2, w2)

            cuadrado = np.ones((max_dim, max_dim, 3), dtype=np.uint8) * 255
            cuadrado[
                (max_dim-h2)//2:(max_dim-h2)//2+h2,
                (max_dim-w2)//2:(max_dim-w2)//2+w2
            ] = recorte

            pred = model.predict(source=cuadrado, verbose=False, conf=0.35)

            if len(pred) > 0 and pred[0].probs is not None:
                idx = pred[0].probs.top1
                voto = pred[0].names[idx]
                datos["historial_votos"].append(voto)

        if datos["frames_visto"] >= 12 and datos["historial_votos"]:
            ganador = max(set(datos["historial_votos"]),
                          key=datos["historial_votos"].count)

            mapa = {
                "plus": "+",
                "minus": "-",
                "multiply": "X",
                "divide": "/",
                "equal": "=",
                "open_paren": "(",
                "close_paren": ")"
            }

            datos["char"] = mapa.get(ganador, ganador)

    for id_reg in list(memoria_pizarra.keys()):
        if id_reg not in casillas_actualizadas:
            memoria_pizarra[id_reg]["frames_ausente"] += 1
            if memoria_pizarra[id_reg]["frames_ausente"] >= 15:
                del memoria_pizarra[id_reg]

    elementos = [d for d in memoria_pizarra.values() if d["char"] is not None]
    elementos = sorted(elementos, key=lambda k: k["bbox"][0])

    return "".join([e["char"] for e in elementos])

if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        exit()

    print("MODELO A TEST")
    print("SPACE = capturar frame")
    print("Q = salir")

    frame_capturado = None
    modo_freeze = False

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_visual = frame.copy()

        # ROI azul SIEMPRE
        frame_visual = dibujar_roi(frame_visual)

        # Si no está congelado → procesar en vivo
        if not modo_freeze:
            resultado = detectar_numero(frame_visual)
        else:
            resultado = detectar_numero(frame_capturado)

        cv2.putText(frame_visual, f"Resultado: {resultado}",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2)

        if modo_freeze:
            cv2.putText(frame_visual, "CAPTURA FIJA (SPACE para continuar)",
                        (30, 90),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2)

        cv2.imshow("MODELO A TEST", frame_visual)

        key = cv2.waitKey(1) & 0xFF

        # SALIR
        if key == ord('q'):
            break

        # CAPTURA FRAME
        elif key == 32:  # SPACE
            if not modo_freeze:
                frame_capturado = frame.copy()
                modo_freeze = True
            else:
                modo_freeze = False

    cap.release()
    cv2.destroyAllWindows()