import cv2
import numpy as np

AREA_MIN = 4000
AREA_MAX = 100000
MARGEN = 10

def contar_objetos(frame):
    """
    Recibe un frame de OpenCV desde main.py, aplica filtros
    morfológicos y devuelve el número entero de objetos encontrados.
    """
    if frame is None:
        return 0

    alto_frame, ancho_frame = frame.shape[:2]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blur, 85, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((5, 5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    contador = 0

    for c in contours:
        area = cv2.contourArea(c)


        if area < AREA_MIN or area > AREA_MAX:
            continue

        x, y, w, h = cv2.boundingRect(c)

        if x <= MARGEN or y <= MARGEN or (x + w) >= ancho_frame - MARGEN or (y + h) >= alto_frame - MARGEN:
            continue

        rel = w / h
        if rel < 0.5 or rel > 2.0:
            continue

        per = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * per, True)

        if len(approx) > 25:
            continue

        contador += 1

    return contador