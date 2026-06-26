import cv2
import numpy as np
from ultralytics import YOLO

# =========================================================
# MODELO (carga única)
# =========================================================
ruta_modelo = "weights/best.pt"
model = YOLO(ruta_modelo)

# =========================================================
# MEMORIA GLOBAL
# =========================================================
memoria_pizarra = {}
ID_CONTADOR = 0

X_MIN_ROI, X_MAX_ROI = 20, 620
Y_MIN_ROI, Y_MAX_ROI = 20, 440

# =========================================================
# MAPA DE CLASES
# =========================================================
MAPA = {
    "plus": "+",
    "minus": "-",
    "multiply": "X",
    "divide": "/",
    "equal": "=",
    "open_paren": "(",
    "close_paren": ")"
}

# =========================================================
# FUNCIÓN PRINCIPAL (USABLE EN MAIN / TKINTER)
# =========================================================
def detectar_numero(frame, debug=False):

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

    mascara_total = mascara_negro | mascara_azul | mascara_rojo

    # ROI
    mascara_roi = np.zeros_like(mascara_total)
    mascara_roi[Y_MIN_ROI:Y_MAX_ROI, X_MIN_ROI:X_MAX_ROI] = 255

    mascara_limpia = cv2.bitwise_and(mascara_total, mascara_roi)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_CLOSE, kernel, iterations=1)

    pizarra = cv2.bitwise_and(frame, frame, mask=mascara_limpia)

    contornos, _ = cv2.findContours(mascara_limpia, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    activos = set()

    for c in contornos:

        x, y, w, h = cv2.boundingRect(c)

        if not (12 < w < 110 and 6 < h < 110):
            continue

        if (x <= X_MIN_ROI + 12 or x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or y + h >= Y_MAX_ROI - 5):
            continue

        cx, cy = x + w // 2, y + h // 2

        # tracking simple
        id_asociado = None

        for i, d in memoria_pizarra.items():
            bx, by, bw, bh = d["bbox"]
            if abs(cx - (bx + bw//2)) < 25 and abs(cy - (by + bh//2)) < 25:
                id_asociado = i
                break

        if id_asociado is None:
            id_asociado = ID_CONTADOR
            memoria_pizarra[id_asociado] = {
                "char": None,
                "bbox": (x, y, w, h),
                "frames": 0,
                "votes": [],
                "lost": 0
            }
            ID_CONTADOR += 1

        activos.add(id_asociado)
        d = memoria_pizarra[id_asociado]

        d["bbox"] = (x, y, w, h)
        d["lost"] = 0

        if d["char"] is not None:
            continue

        d["frames"] += 1

        # crop
        margin = 10
        crop = pizarra[
            max(0, y-margin):min(frame.shape[0], y+h+margin),
            max(0, x-margin):min(frame.shape[1], x+w+margin)
        ]

        if crop.size > 0:
            h2, w2 = crop.shape[:2]
            size = max(h2, w2)

            square = np.ones((size, size, 3), dtype=np.uint8) * 255
            square[(size-h2)//2:(size-h2)//2+h2,
                   (size-w2)//2:(size-w2)//2+w2] = crop

            pred = model.predict(square, verbose=False, conf=0.35)

            if len(pred) > 0 and pred[0].probs is not None:
                idx = pred[0].probs.top1
                label = pred[0].names[idx]
                d["votes"].append(label)

        # estabilización
        if d["frames"] >= 12 and d["votes"]:
            winner = max(set(d["votes"]), key=d["votes"].count)
            d["char"] = MAPA.get(winner, winner)

    # limpieza memoria
    for i in list(memoria_pizarra.keys()):
        if i not in activos:
            memoria_pizarra[i]["lost"] += 1
            if memoria_pizarra[i]["lost"] > 15:
                del memoria_pizarra[i]

    # output final
    items = [d for d in memoria_pizarra.values() if d["char"] is not None]
    items = sorted(items, key=lambda k: k["bbox"][0])

    return "".join([i["char"] for i in items])

# =========================================================
# MODO PRUEBA (IMPORTANTE PARA TI)
# =========================================================
if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        exit()

    print("====================================")
    print(" MODELO A EN MODO PRUEBA")
    print(" ENTER: evaluar frame")
    print(" Q: salir")
    print("====================================")

    ultimo_frame = None
    resultado = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        ultimo_frame = frame.copy()

        # ROI VISUAL (IMPORTANTE PARA GUI TAMBIÉN)
        cv2.rectangle(frame,
                      (X_MIN_ROI, Y_MIN_ROI),
                      (X_MAX_ROI, Y_MAX_ROI),
                      (255, 0, 0), 2)

        # resultado live opcional
        cv2.putText(frame, f"Resultado: {resultado}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2)

        cv2.imshow("MODELO A TEST", frame)

        key = cv2.waitKey(1) & 0xFF

        # ENTER o SPACE -> evaluar frame
        if key == 13 or key == 32:

            resultado = detectar_numero(ultimo_frame)
            print("EXPRESION DETECTADA:", resultado)

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()