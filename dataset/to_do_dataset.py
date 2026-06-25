import cv2
import os
import re

# =========================
# CONFIG
# =========================

url = "http://192.168.26.2:8080/video"

SAVE_DIR = "dataset_math"

classes = {
    ord('0'): "0",
    ord('1'): "1",
    ord('2'): "2",
    ord('3'): "3",
    ord('4'): "4",
    ord('5'): "5",
    ord('6'): "6",
    ord('7'): "7",
    ord('8'): "8",
    ord('9'): "9",

    ord('+'): "plus",
    ord('-'): "minus",
    ord('*'): "multiply",
    ord('/'): "divide",
    ord('='): "equal",

    ord('('): "open_paren",
    ord(')'): "close_paren"
}

# =========================
# CREAR CARPETAS
# =========================

for cls in classes.values():
    os.makedirs(os.path.join(SAVE_DIR, cls), exist_ok=True)

# =========================
# FUNCION PARA OBTENER
# EL SIGUIENTE NUMERO
# =========================

def next_index(folder, prefix):

    max_num = 0

    for file in os.listdir(folder):

        match = re.match(rf"{prefix}_(\d+)\.jpg", file)

        if match:
            n = int(match.group(1))
            max_num = max(max_num, n)

    return max_num + 1

# =========================
# CAMARA
# =========================

cap = cv2.VideoCapture(url)

cv2.namedWindow("Camara", cv2.WINDOW_NORMAL)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    original = frame.copy()

    display = cv2.rotate(original, cv2.ROTATE_90_CLOCKWISE)

    cv2.putText(display,
                "0-9, + - * / = ( ) para guardar | q para salir",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0,255,0),
                2)

    cv2.imshow("Camara", display)

    key = cv2.waitKey(1) & 0xFF

    # salir
    if key == ord('q'):
        break

    # guardar imagen
    if key in classes:

        cls = classes[key]

        folder = os.path.join(SAVE_DIR, cls)

        idx = next_index(folder, cls)

        filename = f"{cls}_{idx}.jpg"

        filepath = os.path.join(folder, filename)

        cv2.imwrite(filepath, original)

        print(f"Guardado: {filepath}")

cap.release()
cv2.destroyAllWindows()