import cv2
import numpy as np
from ultralytics import YOLO

# =========================================================
# MODELO YOLO (APUNTANDO A TU NUEVO PRO DE 11 CLASES)
# =========================================================
ruta_modelo = "weights/best.pt"
model = YOLO(ruta_modelo)

# =========================================================
# CÁMARA
# =========================================================
cam = None

# =========================================================
# MEMORIA GLOBAL
# =========================================================
memoria_pizarra = {}
ID_CONTADOR = 0

# =========================================================
# REGIÓN DE INTERÉS (ROI)
# =========================================================
X_MIN_ROI = 20
X_MAX_ROI = 620

Y_MIN_ROI = 20
Y_MAX_ROI = 440


# =========================================================
# MANEJO DE CÁMARA
# =========================================================

def iniciar_camara(indice=0):
    """
    Abre la cámara.
    """

    global cam

    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        raise Exception("No se pudo abrir la cámara")

    return cam


def obtener_frame():
    """
    Lee un frame de la cámara y dibuja el ROI.
    """

    global cam

    if cam is None:
        return None

    ret, frame = cam.read()

    if not ret:
        return None

    frame = dibujar_roi(frame)

    return frame


def cerrar_camara():
    """
    Libera la cámara.
    """

    global cam

    if cam is not None:
        cam.release()

    cam = None


def resetear_memoria():
    """
    Borra la memoria temporal del detector.
    Debe llamarse antes de evaluar un nuevo ejercicio.
    """

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0

# =========================================================
# DETECCIÓN DEL NÚMERO (FILTRO DE RUIDO DIURNO CALIBRADO)
# =========================================================

def detectar_numero(frame):

    global memoria_pizarra
    global ID_CONTADOR

    if frame is None:
        return ""

    # 1. Segmentación adaptativa diurna estable
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    mascara_total = cv2.adaptiveThreshold(
        gris, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        15, 
        7
    )

    mascara_roi = np.zeros_like(mascara_total)
    mascara_roi[Y_MIN_ROI:Y_MAX_ROI, X_MIN_ROI:X_MAX_ROI] = 255
    mascara_limpia = cv2.bitwise_and(mascara_total, mascara_roi)

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 3)
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )

    pizarra_perfecta = cv2.bitwise_or(
        cv2.bitwise_and(frame, frame, mask=mascara_limpia),
        cv2.bitwise_and(
            np.ones_like(frame) * 255,
            np.ones_like(frame) * 255,
            mask=cv2.bitwise_not(mascara_limpia)
        )
    )

    contornos, _ = cv2.findContours(
        mascara_limpia,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    casillas_actualizadas = set()

    for c in contornos:

        x, y, w, h = cv2.boundingRect(c)

        # ----------------------------------------------------------------------
        # FILTRO DE RUIDO SUTIL RE-CALIBRADO:
        # Exigimos un ancho mínimo de 8 píxeles y una altura de 12 píxeles.
        # Esto anula quirúrgicamente las motas de polvo y manchas de luz inferiores
        # sin comprometer las dimensiones de tus números ni del signo menos real.
        # ----------------------------------------------------------------------
        if w < 8 or h < 12:
            continue

        centro_x = x + w // 2
        centro_y = y + h // 2

        id_asociado = None

        for id_reg, datos in memoria_pizarra.items():

            bx, by, bw, bh = datos["bbox"]

            if (
                abs(centro_x - (bx + bw // 2)) < 25 and
                abs(centro_y - (by + bh // 2)) < 25
            ):
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

            cuadrado = np.ones(
                (max_dim, max_dim, 3),
                dtype=np.uint8
            ) * 255

            cuadrado[
                (max_dim-h2)//2:(max_dim-h2)//2+h2,
                (max_dim-w2)//2:(max_dim-w2)//2+w2
            ] = recorte

            pred = model.predict(
                source=cuadrado,
                verbose=False,
                conf=0.25
            )

            if len(pred) > 0 and pred[0].probs is not None:
                idx = pred[0].probs.top1
                voto_actual = pred[0].names[idx]
                datos["historial_votos"].append(voto_actual)

        if datos["frames_visto"] >= 12 and datos["historial_votos"]:

            ganador = max(
                set(datos["historial_votos"]),
                key=datos["historial_votos"].count
            )

            mapa = {
                "minus": "-"
            }

            datos["char"] = mapa.get(ganador, ganador)

    # -----------------------------------------
    # Limpieza de memoria
    # -----------------------------------------

    for id_reg in list(memoria_pizarra.keys()):

        if id_reg not in casillas_actualizadas:

            memoria_pizarra[id_reg]["frames_ausente"] += 1

            if memoria_pizarra[id_reg]["frames_ausente"] >= 15:

                del memoria_pizarra[id_reg]

    # --- RENDERIZADO VISUAL: Rectángulos de enclavamiento verdes ---
    for id_reg, datos_box in memoria_pizarra.items():
        if datos_box["char"] is not None:
            bx, by, bw, bh = datos_box["bbox"]
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv2.putText(frame, datos_box["char"], (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # -----------------------------------------
    # Construcción del resultado
    # -----------------------------------------

    elementos = [
        d for d in memoria_pizarra.values()
        if d["char"] is not None
    ]

    elementos = sorted(
        elementos,
        key=lambda k: k["bbox"][0]
    )

    resultado = "".join(
        [e["char"] for e in elementos]
    )

    return resultado

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def dibujar_roi(frame):
    """
    Dibuja el recuadro guía azul sobre el frame.
    Puede llamarse tanto desde el modo de prueba
    como desde la interfaz gráfica.
    """

    cv2.rectangle(
        frame,
        (X_MIN_ROI, Y_MIN_ROI),
        (X_MAX_ROI, Y_MAX_ROI),
        (255, 0, 0),
        2
    )

    return frame


def evaluar_frame(frame):
    """
    Evalúa únicamente un frame.

    Pensada para cuando el usuario pulse
    el botón Capturar en la interfaz
    o SPACE en el modo de prueba.
    """
    cadena_final = ""
    for _ in range(15):
        cadena_final = detectar_numero(frame)
    return cadena_final


def limpiar_memoria():
    """
    Reinicia completamente la memoria del detector.

    Debe llamarse cuando inicia una nueva pregunta,
    para que no recuerde números anteriores.
    """

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0

# =========================================================
# MODO DE PRUEBA
# =========================================================

if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        exit()

    print("=====================================")
    print("   MODELO A V2 - CALIBRACIÓN FINAL")
    print("=====================================")
    print("ESPACIO -> Capturar y evaluar")
    print("ESPACIO -> Continuar cámara")
    print("Q -> Salir")
    print("=====================================")

    modo_captura = False

    frame_congelado = None

    resultado = ""

    while True:

        if not modo_captura:

            ret, frame = cap.read()

            if not ret:
                continue

            frame_visual = frame.copy()

            dibujar_roi(frame_visual)

        else:

            frame_visual = frame_congelado.copy()

            dibujar_roi(frame_visual)

        cv2.putText(
            frame_visual,
            f"Resultado: {resultado}",
            (25,45),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0,255,0),
            2
        )

        if modo_captura:

            cv2.putText(
                frame_visual,
                "CAPTURA FIJA",
                (25,85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0,0,255),
                2
            )

        cv2.imshow("MODELO A", frame_visual)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("q"):
            break

        elif tecla == 32:

            if not modo_captura:

                frame_congelado = frame.copy()

                limpiar_memoria()

                resultado = evaluar_frame(frame_congelado)

                modo_captura = True

                print("--------------------------------")
                print("Resultado:", resultado)
                print("--------------------------------")

            else:

                limpiar_memoria()

                resultado = ""

                modo_captura = False

    cap.release()

    cv2.destroyAllWindows()