import cv2
import numpy as np
from ultralytics import YOLO

ruta_modelo = "weights/best.pt"
model = YOLO(ruta_modelo)

cam = None

memoria_pizarra = {}
ID_CONTADOR = 0

X_MIN_ROI = 20
X_MAX_ROI = 620

Y_MIN_ROI = 20
Y_MAX_ROI = 440



def iniciar_camara(indice=0):

    global cam

    cam = cv2.VideoCapture(indice)

    if not cam.isOpened():
        raise Exception("No se pudo abrir la cámara")

    return cam


def obtener_frame():

    global cam

    if cam is None:
        return None

    ret, frame = cam.read()

    if not ret:
        return None

    frame = dibujar_roi(frame)

    return frame


def cerrar_camara():

    global cam

    if cam is not None:
        cam.release()

    cam = None


def resetear_memoria():

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0


def detectar_numero(frame):

    global memoria_pizarra
    global ID_CONTADOR

    if frame is None:
        return ""

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

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_CLOSE, kernel, iterations=1)

    pizarra_perfecta = cv2.bitwise_or(
        cv2.bitwise_and(frame, frame, mask=mascara_limpia),
        cv2.bitwise_and(np.ones_like(frame) * 255, np.ones_like(frame) * 255, mask=cv2.bitwise_not(mascara_limpia))
    )

    contornos, _ = cv2.findContours(
        mascara_limpia,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    casillas_actualizadas = set()

    for c in contornos:

        x, y, w, h = cv2.boundingRect(c)

        if not (15 < w < 110 and 18 < h < 110):
            continue

        if (
            x <= X_MIN_ROI + 12 or
            x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or
            y + h >= Y_MAX_ROI - 5
        ):
            continue

        relacion_aspecto = h / w
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
                conf=0.10
            )

            if len(pred) > 0 and pred[0].probs is not None:

                top5_indices = pred[0].probs.top5
                name_top1 = pred[0].names[top5_indices[0]]
                pool_candidatos = [pred[0].names[idx] for idx in top5_indices]

                voto_actual = name_top1

                if relacion_aspecto < 0.50 and w > 16:
                    if relacion_aspecto < 0.28: voto_actual = "minus"
                    else: voto_actual = "equal"
                        
                elif voto_actual in ["8", "3"] or ("8" in pool_candidatos[:2] and "3" in pool_candidatos[:2]):
                    recorte_gris = mascara_limpia[y:y+h, x:x+w]
                    alto_c, ancho_c = recorte_gris.shape
                    
                    segmento_izq = recorte_gris[int(alto_c*0.35):int(alto_c*0.65), 0:int(ancho_c*0.35)]
                    densidad_pixeles = np.sum(segmento_izq == 255)
                    
                    if densidad_pixeles < (segmento_izq.size * 0.20):
                        voto_actual = "3"
                    else:
                        voto_actual = "8"

                elif h > 20 and 1.2 <= relacion_aspecto <= 2.2:
                    if voto_actual == "1" and "divide" in pool_candidatos[:2] and relacion_aspecto >= 1.6:
                        voto_actual = "divide"
                    elif voto_actual == "8" and "7" in pool_candidatos[:3]:
                        voto_actual = "7"

                if voto_actual != "":
                    datos["historial_votos"].append(voto_actual)

        if datos["frames_visto"] >= 12 and datos["historial_votos"]:

            ganador = max(
                set(datos["historial_votos"]),
                key=datos["historial_votos"].count
            )

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

    for id_reg, datos_box in memoria_pizarra.items():
        if datos_box["char"] is not None:
            bx, by, bw, bh = datos_box["bbox"]
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv2.putText(frame, datos_box["char"], (bx, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


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


def dibujar_roi(frame):

    cv2.rectangle(
        frame,
        (X_MIN_ROI, Y_MIN_ROI),
        (X_MAX_ROI, Y_MAX_ROI),
        (255, 0, 0),
        2
    )

    return frame


def evaluar_frame(frame):
    cadena_final = ""
    for _ in range(15):
        cadena_final = detectar_numero(frame)
    return cadena_final


def limpiar_memoria():

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0


if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        exit()


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

                print("Resultado:", resultado)

            else:

                limpiar_memoria()

                resultado = ""

                modo_captura = False

    cap.release()

    cv2.destroyAllWindows()
