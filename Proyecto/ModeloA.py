import cv2
import numpy as np
from ultralytics import YOLO


RUTA_MODELO = "weights/best.pt"

model = YOLO(RUTA_MODELO)

X_MIN_ROI = 20
X_MAX_ROI = 620
Y_MIN_ROI = 20
Y_MAX_ROI = 440


memoria_pizarra = {}
ID_CONTADOR = 0


def abrir_camara(indice=1):

    cap = cv2.VideoCapture(indice)

    cap.set(cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*'MJPG'))

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)

    if not cap.isOpened():
        raise Exception("No se pudo abrir la cámara.")

    return cap



def reiniciar_memoria():

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0


def procesar_frame(frame):

    global memoria_pizarra
    global ID_CONTADOR

    imagen_visual = frame.copy()

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)


    mascara_negro = cv2.inRange(
        hsv,
        np.array([0, 0, 0]),
        np.array([180, 255, 85])
    )

    mascara_azul = cv2.inRange(
        hsv,
        np.array([90, 45, 30]),
        np.array([135, 255, 255])
    )

    mascara_rojo = cv2.bitwise_or(

        cv2.inRange(
            hsv,
            np.array([0,50,30]),
            np.array([12,255,255])
        ),

        cv2.inRange(
            hsv,
            np.array([155,50,30]),
            np.array([180,255,255])
        )

    )

    mascara_total = cv2.bitwise_or(
        cv2.bitwise_or(mascara_negro, mascara_azul),
        mascara_rojo
    )


    mascara_roi = np.zeros_like(mascara_total)

    mascara_roi[
        Y_MIN_ROI:Y_MAX_ROI,
        X_MIN_ROI:X_MAX_ROI
    ] = 255

    mascara_limpia = cv2.bitwise_and(
        mascara_total,
        mascara_roi
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3,3)
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )

    pizarra_perfecta = cv2.bitwise_or(

        cv2.bitwise_and(
            frame,
            frame,
            mask=mascara_limpia
        ),

        cv2.bitwise_and(
            np.ones_like(frame)*255,
            np.ones_like(frame)*255,
            mask=cv2.bitwise_not(mascara_limpia)
        )

    )


    contornos, _ = cv2.findContours(
        mascara_limpia,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    casillas_actualizadas = set()

    for contorno in contornos:

        x,y,w,h = cv2.boundingRect(contorno)

        if w <= 12 or h <= 6:
            continue

        if w >= 110 or h >= 110:
            continue

        if (
            x <= X_MIN_ROI + 12 or
            x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or
            y + h >= Y_MAX_ROI - 5
        ):
            continue

        centro_x = x + w//2
        centro_y = y + h//2

        id_asociado = None

        for id_reg,datos in memoria_pizarra.items():

            bx,by,bw,bh = datos["bbox"]

            if (
                abs(centro_x-(bx+bw//2)) < 25 and
                abs(centro_y-(by+bh//2)) < 25
            ):

                id_asociado = id_reg
                break

        if id_asociado is None:

            id_asociado = ID_CONTADOR

            memoria_pizarra[id_asociado] = {

                "char":None,

                "bbox":(x,y,w,h),

                "frames_visto":0,

                "historial_votos":[],

                "frames_ausente":0

            }

            ID_CONTADOR += 1

        casillas_actualizadas.add(id_asociado)

        datos = memoria_pizarra[id_asociado]

        datos["frames_ausente"] = 0

        datos["bbox"] = (x,y,w,h)

        if datos["char"] is not None:
            continue

        datos["frames_visto"] += 1

        margen = 10

        recorte_raw = pizarra_perfecta[
            max(0,y-margen):min(frame.shape[0],y+h+margen),
            max(0,x-margen):min(frame.shape[1],x+w+margen)
        ]

        if recorte_raw.size > 0:

            alto_r, ancho_r, _ = recorte_raw.shape

            max_dim = max(alto_r,ancho_r)

            recorte_cuadrado = np.ones(
                (max_dim,max_dim,3),
                dtype=np.uint8
            )*255

            recorte_cuadrado[
                (max_dim-alto_r)//2:(max_dim-alto_r)//2+alto_r,
                (max_dim-ancho_r)//2:(max_dim-ancho_r)//2+ancho_r
            ] = recorte_raw

            pred = model.predict(

                source=recorte_cuadrado,

                verbose=False,

                conf=0.35

            )

            if len(pred)>0 and pred[0].probs is not None:

                idx = pred[0].probs.top1

                voto = pred[0].names[idx]

                datos["historial_votos"].append(voto)

        if datos["frames_visto"] >= 12:

            votos = datos["historial_votos"]

            if votos:

                ganador = max(
                    set(votos),
                    key=votos.count
                )

                if ganador=="plus":
                    ganador="+"

                elif ganador=="minus":
                    ganador="-"

                elif ganador=="multiply":
                    ganador="X"

                elif ganador=="divide":
                    ganador="/"

                elif ganador=="equal":
                    ganador="="

                elif ganador=="open_paren":
                    ganador="("

                elif ganador=="close_paren":
                    ganador=")"

                datos["char"] = ganador

def procesar_frame(frame):
    """
    Procesa un frame y actualiza la memoria de detecciones.

    Retorna:
        imagen_visual
    """

    global memoria_pizarra, ID_CONTADOR

    imagen_visual = frame.copy()

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mascara_negro = cv2.inRange(
        hsv,
        np.array([0, 0, 0]),
        np.array([180, 255, 85])
    )

    mascara_azul = cv2.inRange(
        hsv,
        np.array([90, 45, 30]),
        np.array([135, 255, 255])
    )

    mascara_rojo = cv2.bitwise_or(
        cv2.inRange(hsv,
                    np.array([0,50,30]),
                    np.array([12,255,255])),
        cv2.inRange(hsv,
                    np.array([155,50,30]),
                    np.array([180,255,255]))
    )

    mascara_total = cv2.bitwise_or(
        cv2.bitwise_or(mascara_negro, mascara_azul),
        mascara_rojo
    )

    mascara_roi = np.zeros_like(mascara_total)

    mascara_roi[
        Y_MIN_ROI:Y_MAX_ROI,
        X_MIN_ROI:X_MAX_ROI
    ] = 255

    mascara_limpia = cv2.bitwise_and(
        mascara_total,
        mascara_roi
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3,3)
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
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
            np.ones_like(frame)*255,
            np.ones_like(frame)*255,
            mask=cv2.bitwise_not(mascara_limpia)
        )
    )

    contornos, _ = cv2.findContours(
        mascara_limpia,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    casillas_actualizadas = set()

    for contorno in contornos:

        x, y, w, h = cv2.boundingRect(contorno)

        if not (w > 12 and h > 6 and w < 110 and h < 110):
            continue

        if (x <= X_MIN_ROI + 12 or
            x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or
            y + h >= Y_MAX_ROI - 5):
            continue

        centro_x = x + w//2
        centro_y = y + h//2

        id_asociado = None

        for id_reg, datos in memoria_pizarra.items():

            bx, by, bw, bh = datos["bbox"]

            if (abs(centro_x-(bx+bw//2)) < 25 and
                abs(centro_y-(by+bh//2)) < 25):

                id_asociado = id_reg
                break

        if id_asociado is None:

            id_asociado = ID_CONTADOR

            memoria_pizarra[id_asociado] = {
                "char": None,
                "bbox": (x,y,w,h),
                "frames_visto": 0,
                "historial_votos": [],
                "frames_ausente": 0
            }

            ID_CONTADOR += 1

        casillas_actualizadas.add(id_asociado)

        datos = memoria_pizarra[id_asociado]

        datos["frames_ausente"] = 0
        datos["bbox"] = (x,y,w,h)

        if datos["char"] is not None:
            continue

        datos["frames_visto"] += 1

        margen = 10

        recorte = pizarra_perfecta[
            max(0,y-margen):min(frame.shape[0],y+h+margen),
            max(0,x-margen):min(frame.shape[1],x+w+margen)
        ]

        if recorte.size == 0:
            continue

        alto, ancho = recorte.shape[:2]

        lado = max(alto, ancho)

        cuadrado = np.ones(
            (lado,lado,3),
            dtype=np.uint8
        )*255

        cuadrado[
            (lado-alto)//2:(lado-alto)//2+alto,
            (lado-ancho)//2:(lado-ancho)//2+ancho
        ] = recorte

        pred = model.predict(
            source=cuadrado,
            verbose=False,
            conf=0.35
        )

        if len(pred) > 0 and pred[0].probs is not None:

            idx = pred[0].probs.top1
            voto = pred[0].names[idx]

            datos["historial_votos"].append(voto)

        if datos["frames_visto"] >= 12:

            votos = datos["historial_votos"]

            if votos:

                ganador = max(
                    set(votos),
                    key=votos.count
                )

                # Como este módulo solo devuelve números,
                # ignoramos operadores.

                if ganador.isdigit():
                    datos["char"] = ganador

def abrir_camara():
    """
    Inicializa la cámara USB y devuelve el objeto VideoCapture.
    """

    cap = cv2.VideoCapture(CAMARA)

    cap.set(cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*'MJPG'))

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)

    if not cap.isOpened():
        raise Exception("No se pudo abrir la cámara.")

    return cap


def reiniciar_memoria():
    """
    Borra todas las detecciones anteriores.
    Debe llamarse antes de iniciar una nueva captura.
    """

    global memoria_pizarra
    global ID_CONTADOR

    memoria_pizarra = {}
    ID_CONTADOR = 0


def obtener_numero():
    """
    Construye el número a partir de los caracteres
    reconocidos por YOLO.

    Retorna:
        int  -> número detectado
        None -> si no se detectó ningún número válido
    """

    elementos = [
        datos
        for datos in memoria_pizarra.values()
        if datos["char"] is not None
    ]

    if len(elementos) == 0:
        return None

    # Ordenar de izquierda a derecha
    elementos = sorted(
        elementos,
        key=lambda x: x["bbox"][0]
    )

    numero = ""

    for elemento in elementos:

        caracter = str(elemento["char"])

        # En este módulo solamente aceptamos dígitos
        if caracter.isdigit():
            numero += caracter

    if numero == "":
        return None

    return int(numero)


def procesar_frame(frame):

    global memoria_pizarra
    global ID_CONTADOR

    imagen_visual = frame.copy()

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mascara_negro = cv2.inRange(
        hsv,
        np.array([0, 0, 0]),
        np.array([180, 255, 85])
    )

    mascara_azul = cv2.inRange(
        hsv,
        np.array([90, 45, 30]),
        np.array([135, 255, 255])
    )

    mascara_rojo = cv2.bitwise_or(

        cv2.inRange(
            hsv,
            np.array([0, 50, 30]),
            np.array([12, 255, 255])
        ),

        cv2.inRange(
            hsv,
            np.array([155, 50, 30]),
            np.array([180, 255, 255])
        )
    )

    mascara_total = cv2.bitwise_or(
        cv2.bitwise_or(
            mascara_negro,
            mascara_azul
        ),
        mascara_rojo
    )

    mascara_roi = np.zeros_like(mascara_total)

    mascara_roi[
        Y_MIN_ROI:Y_MAX_ROI,
        X_MIN_ROI:X_MAX_ROI
    ] = 255

    mascara_limpia = cv2.bitwise_and(
        mascara_total,
        mascara_roi
    )


    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 3)
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_OPEN,
        kernel,
        iterations=1
    )

    mascara_limpia = cv2.morphologyEx(
        mascara_limpia,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1
    )


    pizarra_perfecta = cv2.bitwise_or(

        cv2.bitwise_and(
            frame,
            frame,
            mask=mascara_limpia
        ),

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

    # Aquí comienza el recorrido de los contornos...
    for contorno in contornos:
        x, y, w, h = cv2.boundingRect(contorno)


        if w <= 12 or h <= 6 or w >= 110 or h >= 110:
            continue


        if (
            x <= X_MIN_ROI + 12 or
            x + w >= X_MAX_ROI - 12 or
            y <= Y_MIN_ROI + 12 or
            y + h >= Y_MAX_ROI - 5
        ):
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

        datos_casilla = memoria_pizarra[id_asociado]

        datos_casilla["frames_ausente"] = 0
        datos_casilla["bbox"] = (x, y, w, h)


        if datos_casilla["char"] is not None:
            continue

        datos_casilla["frames_visto"] += 1


        margen = 10

        recorte_raw = pizarra_perfecta[
            max(0, y - margen):min(frame.shape[0], y + h + margen),
            max(0, x - margen):min(frame.shape[1], x + w + margen)
        ]

        if recorte_raw.size == 0:
            continue

        alto_r, ancho_r, _ = recorte_raw.shape

        max_dim = max(alto_r, ancho_r)

        recorte_cuadrado = np.ones(
            (max_dim, max_dim, 3),
            dtype=np.uint8
        ) * 255

        recorte_cuadrado[
            (max_dim - alto_r)//2:(max_dim - alto_r)//2 + alto_r,
            (max_dim - ancho_r)//2:(max_dim - ancho_r)//2 + ancho_r
        ] = recorte_raw


        prediccion = model.predict(
            source=recorte_cuadrado,
            verbose=False,
            conf=0.35
        )

        if len(prediccion) > 0 and prediccion[0].probs is not None:

            idx_ganador = prediccion[0].probs.top1

            voto_actual = prediccion[0].names[idx_ganador]

            datos_casilla["historial_votos"].append(voto_actual)


        if datos_casilla["frames_visto"] >= 12:

            votos = datos_casilla["historial_votos"]

            if len(votos) > 0:

                ganador = max(
                    set(votos),
                    key=votos.count
                )


                if ganador in MAPEO:
                    ganador = MAPEO[ganador]


                if str(ganador).isdigit():

                    datos_casilla["char"] = ganador

    for id_reg in list(memoria_pizarra.keys()):

        if id_reg not in casillas_actualizadas:

            memoria_pizarra[id_reg]["frames_ausente"] += 1

            if memoria_pizarra[id_reg]["frames_ausente"] >= 15:

                del memoria_pizarra[id_reg]


    for datos in memoria_pizarra.values():

        if datos["char"] is None:
            continue

        bx, by, bw, bh = datos["bbox"]

        cv2.rectangle(
            imagen_visual,
            (bx, by),
            (bx + bw, by + bh),
            (0, 255, 0),
            2
        )

        cv2.putText(
            imagen_visual,
            str(datos["char"]),
            (bx, by - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )


    cv2.rectangle(
        imagen_visual,
        (X_MIN_ROI, Y_MIN_ROI),
        (X_MAX_ROI, Y_MAX_ROI),
        (255, 0, 0),
        1
    )


    return imagen_visual


def capturar_numero(debug=True):
    """
    Abre la cámara y espera hasta que el usuario
    presione ENTER o ESPACIO.

    Retorna:
        int  -> número reconocido
        None -> si no pudo reconocer ninguno
    """

    reiniciar_memoria()

    cap = abrir_camara()

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        imagen = procesar_frame(frame)

        numero = obtener_numero()

        # Mostrar número reconocido
        if numero is not None:

            cv2.putText(
                imagen,
                f"Numero: {numero}",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2
            )

        cv2.putText(
            imagen,
            "ENTER o ESPACIO = Capturar",
            (20,430),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255,255,0),
            2
        )

        cv2.putText(
            imagen,
            "Q = Cancelar",
            (20,460),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,0,255),
            2
        )

        cv2.imshow("Modelo A", imagen)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == 13 or tecla == 32:

            cap.release()
            cv2.destroyAllWindows()

            if debug:
                print(f"[Modelo A] Numero detectado: {numero}")

            return numero

        elif tecla == ord('q'):

            cap.release()
            cv2.destroyAllWindows()

            if debug:
                print("[Modelo A] Captura cancelada.")

            return None
