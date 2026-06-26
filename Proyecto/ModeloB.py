import cv2
import numpy as np

AREA_MIN = 4000
AREA_MAX = 100000
MARGEN = 10


def abrir_camara(index=0):
    cam = cv2.VideoCapture(index)
    if not cam.isOpened():
        raise Exception("No se pudo abrir la cámara")
    return cam


def cerrar_camara(cam):
    cam.release()
    cv2.destroyAllWindows()


def capturar_imagen(cam):
    """
    Muestra la cámara hasta ENTER (13).
    Devuelve el frame capturado.
    """
    while True:
        ret, frame = cam.read()
        if not ret:
            continue

        cv2.putText(frame,
                    "ENTER: capturar | Q: salir",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2)

        cv2.imshow("Camara - Modelo B", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 13:  # ENTER
            return frame

        if key == ord('q'):
            return None


def contar_objetos(frame, debug=False):

    alto, ancho = frame.shape[:2]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    _, thresh = cv2.threshold(blur, 190, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((5, 5), np.uint8)

    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contador = 0

    for c in contours:

        area = cv2.contourArea(c)

        if area < AREA_MIN or area > AREA_MAX:
            continue

        x, y, w, h = cv2.boundingRect(c)

        if x <= MARGEN or y <= MARGEN:
            continue

        if x + w >= ancho - MARGEN:
            continue

        if y + h >= alto - MARGEN:
            continue

        rel = w / h
        if rel < 0.5 or rel > 2.0:
            continue

        per = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * per, True)

        if len(approx) > 25:
            continue

        contador += 1

        if debug:
            cv2.drawContours(frame, [c], -1, (0, 255, 0), 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    if debug:
        cv2.putText(frame,
                    f"Total: {contador}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 255),
                    2)

    return contador, frame, thresh


def ejecutar_modeloB(debug=False):

    cam = abrir_camara()

    try:
        frame = capturar_imagen(cam)

        if frame is None:
            return None

        cantidad, frame_proc, mask = contar_objetos(frame, debug=debug)

        return {
            "cantidad": cantidad,
            "frame": frame,
            "procesada": frame_proc,
            "mascara": mask
        }

    finally:
        cerrar_camara(cam)


if __name__ == "__main__":

    resultado = ejecutar_modeloB(debug=True)

    if resultado is not None:
        print("Cantidad detectada:", resultado["cantidad"])