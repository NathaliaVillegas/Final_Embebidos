import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import re
import os


import ModeloA
import ModeloB
import operaciones
from historial import Historial
from uart import UART

# =========================================================
# NUEVA PALETA DE COLORES (PASTELES: ROSADO, MORADO, TURQUESA)
# =========================================================
COLOR_FONDO = "#F4E8FF"       
COLOR_TEXTO_MAIN = "#351C4D"  
COLOR_TITULO = "#BD1D9D"      
COLOR_MODO_A = "#AE82E1"      
COLOR_MODO_B = "#A0E8DF"      
COLOR_BOTON_OK = "#C3AED6"    
COLOR_BOTON_ERR = "#FF9AA2"   
COLOR_BOTON_NEU = "#B5EAD7"   

# =========================================================
# CONFIGURACIÓN VISUAL Y FUENTES
# =========================================================
ANCHO = 1280
ALTO = 720
FUENTE_TITULO = ("Comic Sans MS", 40, "bold")
FUENTE_TEXTO = ("Comic Sans MS", 24, "bold")
FUENTE_BOTON = ("Comic Sans MS", 14, "bold")

def dibujar_texto_borde(canvas, x, y, texto, fuente, color_texto, color_borde, tag=None, justify="center"):
    """Dibuja texto con contorno para que resalte sobre cualquier imagen de fondo."""
    desp = 2
    opciones = {"text": texto, "font": fuente, "fill": color_borde, "justify": justify}
    if tag: opciones["tags"] = tag
    
    # Sombras / Bordes
    canvas.create_text(x-desp, y-desp, **opciones)
    canvas.create_text(x+desp, y-desp, **opciones)
    canvas.create_text(x-desp, y+desp, **opciones)
    canvas.create_text(x+desp, y+desp, **opciones)
    # Texto principal
    opciones["fill"] = color_texto
    canvas.create_text(x, y, **opciones)


class AccessWindow():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema Educativo Inteligente - Acceso")
        self.root.geometry(f"{ANCHO}x{ALTO}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=ANCHO, height=ALTO, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        try:
            self.img_fondo = ImageTk.PhotoImage(Image.open("fondo_login.jpg").resize((ANCHO, ALTO)))
            self.canvas.create_image(0, 0, image=self.img_fondo, anchor="nw")
        except:
            self.canvas.configure(bg=COLOR_FONDO)

        dibujar_texto_borde(self.canvas, ANCHO//2, 280, "Ingresa tu nombre para comenzar a jugar:", FUENTE_TEXTO, "white", COLOR_TEXTO_MAIN)

        self.name_entry = tk.Entry(self.root, width=75, font=("Comic Sans MS", 18), justify="center", bg="white", fg=COLOR_TEXTO_MAIN, relief="flat", bd=0)
        self.name_entry.place(x=220, y=340, height=50)
        self.name_entry.focus()

        guardar = tk.Button(self.root, text="¡Entrar a Jugar!", font=FUENTE_BOTON, command=self.started, 
                            bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, activebackground="#D5C5E3", relief="flat")
        guardar.place(x=ANCHO//2 - 100, y=450, width=200, height=50)

        btn_salir = tk.Button(self.root, text="Salir", font=FUENTE_BOTON, command=self.root.destroy, 
                              bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, relief="flat")
        btn_salir.place(x=20, y=20, width=100, height=45)

        self.root.bind("<Return>", lambda e: self.started())
        self.root.mainloop()

    def started(self):
        nombre = self.name_entry.get().strip()
        if nombre != "":
            self.root.destroy()
            MainWindow(nombre)
        else:
            messagebox.showwarning("Atención", "Debes escribir tu nombre para continuar.")

class MainWindow():
    def __init__(self, user_name):
        self.root = tk.Tk()
        self.root.title("Sistema Educativo Inteligente - Panel Principal")
        self.root.geometry(f"{ANCHO}x{ALTO}")
        self.root.resizable(False, False)
        
        # --- Inicialización de Hardware y Persistencia (Intacto) ---
        self.uart = UART(port="/dev/serial0", baudrate=9600)
        self.historial = Historial(user_name)
        self.cam = None
        
        # --- Variables de control (Intacto) ---
        self.modo_actual = 0
        self.total_intentos = 0
        self.intento_actual = 0
        self.ejercicio_str = ""
        self.respuesta_esperada = 0
        self.objetos_detectados = 0
        self.estado_juego = ""  
        self.frame_actual = None
        self.frame_congelado = None
        self.video_pausado = False
        self.estado_memoria = ""

        # Contenedor principal
        self.canvas = tk.Canvas(self.root, width=ANCHO, height=ALTO, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.root.bind('<Return>', self.tecla_presionada)
        self.root.bind('<space>', self.tecla_presionada)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_todo)

        self.crear_pantalla_menu()
        self.root.mainloop()

    def cargar_fondo(self, nombre_archivo):
        self.canvas.delete("all")
        try:
            self.img_fondo = ImageTk.PhotoImage(Image.open(nombre_archivo).resize((ANCHO, ALTO)))
            self.canvas.create_image(0, 0, image=self.img_fondo, anchor="nw")
        except:
            self.canvas.configure(bg=COLOR_FONDO)

    def destruir_widgets(self):
        for widget in self.root.winfo_children():
            if isinstance(widget, (tk.Button, tk.Entry, tk.Label)):
                widget.destroy()

    def botones_navegacion(self, comando_volver=None):
        if comando_volver:
            btn_volver = tk.Button(self.root, text="Volver", font=FUENTE_BOTON, command=comando_volver, 
                                   bg=COLOR_BOTON_NEU, fg=COLOR_TEXTO_MAIN, relief="flat")
            btn_volver.place(x=20, y=20, width=120, height=45)

        btn_salir = tk.Button(self.root, text="Salir", font=FUENTE_BOTON, command=self.cerrar_todo, 
                              bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, relief="flat")
        btn_salir.place(x=1140, y=20, width=120, height=45)

    # =========================================================
    # PANTALLAS DE FLUJO DE LA INTERFAZ
    # =========================================================
    def crear_pantalla_menu(self):
        self.destruir_widgets()
        self.detener_camara()
        self.estado_juego = ""
        self.cargar_fondo("fondo_selección.jpg")

        dibujar_texto_borde(self.canvas, ANCHO//2, 185, f"¡Hola, {self.historial.nombre}!", FUENTE_TITULO, "white", COLOR_TITULO)
        dibujar_texto_borde(self.canvas, ANCHO//2, 280, "Selecciona un modo para comenzar a aprender:", FUENTE_TEXTO, "white", COLOR_TEXTO_MAIN)

        btn_a = tk.Button(self.root, text="Modo A: Resolver Operaciones en Pizarra", font=FUENTE_BOTON, 
                          bg=COLOR_MODO_A, fg=COLOR_TEXTO_MAIN, relief="flat", command=lambda: self.pedir_intentos(1))
        btn_a.place(x=230, y=350, width=400, height=200)

        btn_b = tk.Button(self.root, text="Modo B: Conteo de Objetos en Mesa", font=FUENTE_BOTON, 
                          bg=COLOR_MODO_B, fg=COLOR_TEXTO_MAIN, relief="flat", command=lambda: self.pedir_intentos(2))
        btn_b.place(x=650, y=350, width=400, height=200)
        
        self.botones_navegacion()

    def pedir_intentos(self, modo):
        self.destruir_widgets()
        self.modo_actual = modo
        self.cargar_fondo("fondo_intentos.jpg")
        
        titulo_texto = "Modo A: Análisis de Pizarra" if modo == 1 else "Modo B: Conteo de Objetos"
        
        dibujar_texto_borde(self.canvas, ANCHO//2, 150, titulo_texto, FUENTE_TITULO, "white", COLOR_TITULO)
        dibujar_texto_borde(self.canvas, ANCHO//2, 240, "¿Cuántos ejercicios o intentos deseas realizar?", FUENTE_TEXTO, "white", COLOR_TEXTO_MAIN)

        self.entry_intentos = tk.Entry(self.root, font=("Comic Sans MS", 22), justify="center", bg="white", fg=COLOR_TEXTO_MAIN, relief="flat", bd=0)
        self.entry_intentos.place(x=ANCHO//2 - 75, y=320, width=150, height=50)
        self.entry_intentos.focus()

        tk.Button(self.root, text="¡Comenzar Actividad!", font=FUENTE_BOTON, bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, 
                  relief="flat", command=self.validar_e_iniciar).place(x=ANCHO//2 - 125, y=480, width=250, height=60)
                  
        self.botones_navegacion(comando_volver=self.crear_pantalla_menu)

    def validar_e_iniciar(self):
        try:
            self.total_intentos = int(self.entry_intentos.get().strip())
            if self.total_intentos <= 0: raise ValueError
        except:
            messagebox.showerror("Error", "Por favor introduce un número entero de intentos válido.")
            return

        self.intento_actual = 1
        self.historial.iniciar_sesion(f"Modo {self.modo_actual}", intentos=self.total_intentos)
        
        try:
            self.uart.iniciar_juego(self.total_intentos)
        except Exception as e:
            pass
            
        self.construir_interfaz_juego()

    # =========================================================
    # ÁREA DE JUEGO DINÁMICA (Textos en Canvas para no tapar fondo)
    # =========================================================
    def construir_interfaz_juego(self):
        self.destruir_widgets()
        self.cargar_fondo("fondo_camara.jpg")
        self.botones_navegacion(comando_volver=self.crear_pantalla_menu)
        
        # Textos Dinámicos dibujados transparentes sobre el Canvas (Lado Izquierdo)
        dibujar_texto_borde(self.canvas, 430, 220, "", FUENTE_TEXTO, "white", COLOR_TITULO, tag="lbl_contador")
        dibujar_texto_borde(self.canvas, 350, 330, "", FUENTE_TEXTO, "white", COLOR_TEXTO_MAIN, tag="lbl_instruccion")
        dibujar_texto_borde(self.canvas, 350, 480, "", FUENTE_TEXTO, "purple", COLOR_TITULO, tag="lbl_resultado")
        
        # Botones de confirmación (Lado Izquierdo - ocultos por defecto)
        self.btn_enviar = tk.Button(self.root, text="Enviar Captura", font=FUENTE_BOTON, bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, relief="flat", command=self.procesar_captura)
        self.btn_otra = tk.Button(self.root, text="Tomar Otra", font=FUENTE_BOTON, bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, relief="flat", command=self.cancelar_captura)
        
        # Video de la cámara (Lado Derecho)
        self.lbl_video = tk.Label(self.root, bg="black")
        self.lbl_video.place(x=700, y=150, width=500, height=380)
        
        self.iniciar_camara()
        
        if self.modo_actual == 1:
            self.siguiente_intento_m1()
        else:
            self.siguiente_intento_m2_mesa()

    def actualizar_textos_juego(self, contador="", instruccion="", resultado="", color_res="white"):
        if contador:
            self.canvas.itemconfig("lbl_contador", text=contador)
        if instruccion:
            self.canvas.itemconfig("lbl_instruccion", text=instruccion)
        if resultado:
            self.canvas.itemconfig("lbl_resultado", text=resultado, fill=color_res)

    def mostrar_botones_confirmacion(self, mostrar=True):
        if mostrar:
            self.btn_enviar.place(x=150, y=600, width=180, height=50)
            self.btn_otra.place(x=350, y=600, width=180, height=50)
        else:
            self.btn_enviar.place_forget()
            self.btn_otra.place_forget()

    # --- LÓGICA DE SECUENCIA INTACTA ---
    def siguiente_intento_m1(self):
        self.estado_juego = "JUGANDO_M1"
        self.video_pausado = False
        self.mostrar_botones_confirmacion(False)
        
        self.ejercicio_str, self.respuesta_esperada = operaciones.generar_operacion()
        
        self.actualizar_textos_juego(
            contador=f"Ejercicio {self.intento_actual} de {self.total_intentos}",
            instruccion=f"Resuelve en la pizarra:\n\n{self.ejercicio_str} = ?",
            resultado="Alinea el resultado y presiona ESPACIO."
        )
        ModeloA.limpiar_memoria()

    def siguiente_intento_m2_mesa(self):
        self.estado_juego = "M2_MESA"
        self.video_pausado = False
        self.mostrar_botones_confirmacion(False)
        
        self.actualizar_textos_juego(
            contador=f"Conteo {self.intento_actual} de {self.total_intentos}",
            instruccion="Paso 1:\nColoca los objetos que quieras\ncontar sobre la mesa.",
            resultado="Presiona ESPACIO para registrar."
        )

    def siguiente_intento_m2_pizarra(self):
        self.estado_juego = "M2_PIZARRA"
        self.video_pausado = False
        self.mostrar_botones_confirmacion(False)
        
        self.actualizar_textos_juego(
            instruccion="Paso 2:\n¡Objetos registrados!\n\nEscribe el número en tu pizarra.",
            resultado="Encuadra la pizarra y presiona ESPACIO."
        )
        ModeloA.limpiar_memoria()

    # =========================================================
    # CÁMARA Y CAPTURAS (Lógica Intacta)
    # =========================================================
    def iniciar_camara(self):
        if self.cam is None:
            self.cam = cv2.VideoCapture(0) # Ajusta índice si es necesario
            self.video_pausado = False
            self.actualizar_video()

    def detener_camara(self):
        if self.cam is not None:
            self.cam.release()
            self.cam = None

    def actualizar_video(self):
        if self.cam is not None and self.cam.isOpened():
            if not self.video_pausado:
                ret, frame = self.cam.read()
                if ret:
                    self.frame_actual = frame.copy()
                    frame_dibujado = frame.copy()
                    
                    cv2.rectangle(frame_dibujado, (ModeloA.X_MIN_ROI, ModeloA.Y_MIN_ROI), 
                                  (ModeloA.X_MAX_ROI, ModeloA.Y_MAX_ROI), (255, 182, 193), 2)
                    
                    cv2image = cv2.cvtColor(frame_dibujado, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv2image).resize((500, 380), Image.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img)
                    
                    self.lbl_video.imgtk = imgtk
                    self.lbl_video.configure(image=imgtk)
                    
            self.lbl_video.after(30, self.actualizar_video)

    def tecla_presionada(self, event):
        if self.estado_juego in ["JUGANDO_M1", "M2_MESA", "M2_PIZARRA"] and not self.video_pausado:
            if self.frame_actual is not None:
                self.frame_congelado = self.frame_actual.copy()
                self.video_pausado = True 
                self.estado_memoria = self.estado_juego
                self.estado_juego = "CONFIRMANDO"
                
                self.actualizar_textos_juego(resultado="¿La imagen se ve bien?", color_res="purple")
                self.mostrar_botones_confirmacion(True)

    def cancelar_captura(self):
        self.estado_juego = self.estado_memoria
        self.video_pausado = False
        self.mostrar_botones_confirmacion(False)
        self.actualizar_textos_juego(resultado="Presiona ESPACIO cuando estés listo.", color_res="white")

    def procesar_captura(self):
        self.mostrar_botones_confirmacion(False)
        self.actualizar_textos_juego(resultado="Pensando... ", color_res="purple")
        self.root.update()
        
        if self.estado_memoria == "JUGANDO_M1":
            self.evaluar_pizarra_m1(self.frame_congelado)
        elif self.estado_memoria == "M2_MESA":
            self.objetos_detectados = ModeloB.contar_objetos(self.frame_congelado)
            self.siguiente_intento_m2_pizarra()
        elif self.estado_memoria == "M2_PIZARRA":
            self.evaluar_pizarra_m2(self.frame_congelado)


    def evaluar_pizarra_m1(self, frame):
        texto_yolo = ModeloA.evaluar_frame(frame)
        numeros = re.findall(r'\d+', str(texto_yolo))
        
        if not numeros:
            self.actualizar_textos_juego(resultado="No detecté ningún número. ¡Vuelve a intentarlo!", color_res="#FF6B6B")
            self.cancelar_captura()
            return
            
        respuesta_alumno = int(numeros[-1])
        es_correcto = (respuesta_alumno == self.respuesta_esperada)
        
        if es_correcto:
            msj_pantalla = f"¡CORRECTO! 🟢\nEscribiste {respuesta_alumno} muy bien."
        else:
            msj_pantalla = f"INCORRECTO 🔴\nTu respuesta fue {respuesta_alumno},\npero el resultado era {self.respuesta_esperada}."
            
        self.notificar_resultado(f"{self.ejercicio_str} = {respuesta_alumno}", es_correcto, msj_pantalla)

    def evaluar_pizarra_m2(self, frame):
        texto_yolo = ModeloA.evaluar_frame(frame)
        numeros = re.findall(r'\d+', str(texto_yolo))
        
        if not numeros:
            self.actualizar_textos_juego(resultado="No detecté ningún número. ¡Vuelve a intentarlo!", color_res="#FF6B6B")
            self.cancelar_captura()
            return
            
        respuesta_alumno = int(numeros[-1])
        es_correcto = (respuesta_alumno == self.objetos_detectados)
        
        if es_correcto:
            msj_pantalla = f"¡CORRECTO! 🟢\nContaste {respuesta_alumno} objetos perfectamente."
        else:
            msj_pantalla = f"INCORRECTO 🔴\nPusiste {respuesta_alumno} pero en\nrealidad habían {self.objetos_detectados} objetos."
            
        self.notificar_resultado(f"Mesa:{self.objetos_detectados} -> Escrito:{respuesta_alumno}", es_correcto, msj_pantalla)

    def notificar_resultado(self, string_registro, es_correcto, msj_pantalla):
        if es_correcto:
            self.uart.correcto()
            self.actualizar_textos_juego(resultado=msj_pantalla, color_res="#2ECC71") # Verde resaltante
        else:
            self.uart.incorrecto()
            self.actualizar_textos_juego(resultado=msj_pantalla, color_res="#FF6B6B") # Rojo resaltante
            
        self.historial.agregar_resultado(string_registro, "Cámara", es_correcto)
        
        if self.intento_actual < self.total_intentos:
            self.intento_actual += 1
            retardo = 3500 
            if self.modo_actual == 1:
                self.root.after(retardo, self.siguiente_intento_m1)
            else:
                self.root.after(retardo, self.siguiente_intento_m2_mesa)
        else:
            self.root.after(3500, self.crear_pantalla_final)

    # =========================================================
    # PANTALLA FINAL
    # =========================================================
    def crear_pantalla_final(self):
        self.destruir_widgets()
        self.detener_camara()
        self.cargar_fondo("fondo_historial.jpg")
        self.botones_navegacion()
        
        dibujar_texto_borde(self.canvas, ANCHO//2 + 100, 200, "¡Actividad Concluida!", FUENTE_TITULO, "white", COLOR_TITULO)
        
        porcentaje = self.historial.puntaje()
        dibujar_texto_borde(self.canvas, ANCHO//2, 280, f"Respuestas Correctas: {self.historial.correctas}", FUENTE_TEXTO, "#2ECC71", "black")
        dibujar_texto_borde(self.canvas, ANCHO//2, 320, f"Respuestas Incorrectas: {self.historial.incorrectas}", FUENTE_TEXTO, "#FF6B6B", "black")
        dibujar_texto_borde(self.canvas, ANCHO//2, 400, f"Puntaje Final: {porcentaje}%", FUENTE_TITULO, "white", COLOR_MODO_B)
        
        tk.Button(self.root, text="Volver a Jugar este Modo", font=FUENTE_BOTON, bg=COLOR_MODO_A, fg=COLOR_TEXTO_MAIN, 
                  relief="flat", command=lambda: self.pedir_intentos(self.modo_actual)).place(x=ANCHO//2 - 150, y=500, width=300, height=50)
                  
        tk.Button(self.root, text="Ir al Menú de Selección", font=FUENTE_BOTON, bg=COLOR_BOTON_NEU, fg=COLOR_TEXTO_MAIN, 
                  relief="flat", command=self.crear_pantalla_menu).place(x=ANCHO//2 - 150, y=580, width=300, height=50)

    def cerrar_todo(self):
        if self.historial:
            self.historial.finalizar_sesion()
        self.uart.cerrar()
        self.detener_camara()
        self.root.quit()

if __name__ == "__main__":
    access = AccessWindow()