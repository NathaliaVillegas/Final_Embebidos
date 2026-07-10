import tkinter as tk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import re

# --- Importación de tus módulos del sistema educativo ---
import ModeloA
import interfaz as ModeloB  # Tu procesador morfológico de conteo
import operaciones
from historial import Historial
from uart import UART

# =========================================================
# NUEVA PALETA DE COLORES (PASTELES: ROSADO, MORADO, TURQUESA)
# =========================================================
COLOR_FONDO = "#F4E8FF"       # Morado muy pastel (Fondo principal)
COLOR_TEXTO_MAIN = "#4A235A"  # Morado oscuro para el texto (buena legibilidad)
COLOR_TITULO = "#351C4D"      # Morado más oscuro para títulos
COLOR_MODO_A = "#FFB6C1"      # Rosado pastel (Botones Modo 1)
COLOR_MODO_B = "#A0E8DF"      # Turquesa pastel (Botones Modo 2)
COLOR_BOTON_OK = "#C3AED6"    # Morado/Lila pastel intermedio (Confirmar)
COLOR_BOTON_ERR = "#FF9AA2"   # Rosado/Coral pastel (Cancelar/Error)
COLOR_BOTON_NEU = "#B5EAD7"   # Verde/Turquesa suave (Volver/Salir)

class AccessWindow():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema Educativo Inteligente - Acceso")
        self.root.configure(bg=COLOR_FONDO)
        self.root.geometry("800x500")
        self.root.resizable(False, False)

        titulo = tk.Label(self.root, text="¡Bienvenido al Sistema Educativo!", 
                          font=("Century Gothic", 24, "bold"), fg=COLOR_TITULO, bg=COLOR_FONDO)
        titulo.pack(pady=50)

        instruccion = tk.Label(self.root, text="Ingresa tu nombre para comenzar a jugar:", 
                               font=("Century Gothic", 14), fg=COLOR_TEXTO_MAIN, bg=COLOR_FONDO)
        instruccion.pack(pady=10)

        self.name_entry = tk.Entry(self.root, width=40, font=("Century Gothic", 14), justify="center", relief="solid", bd=1)
        self.name_entry.pack(pady=10)
        self.name_entry.focus()

        guardar = tk.Button(self.root, text="¡Entrar a Jugar!", font=("Century Gothic", 12, "bold"),
                            command=self.started, bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, 
                            activebackground="#D5C5E3", relief="flat", padx=20, pady=8)
        guardar.pack(pady=30)

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
        self.root.configure(bg=COLOR_FONDO)
        self.root.geometry("1100x750")
        
        # --- Inicialización de Hardware y Persistencia ---
        self.uart = UART(port="/dev/serial0", baudrate=9600)
        self.historial = Historial(user_name)
        self.cam = None
        
        # --- Variables de control de los modos de juego ---
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

        self.root.bind('<Return>', self.tecla_presionada)
        self.root.bind('<space>', self.tecla_presionada)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_todo)

        self.crear_pantalla_menu()
        self.root.mainloop()

    def limpiar_pantalla(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # =========================================================
    # PANTALLAS DE FLUJO DE LA INTERFAZ
    # =========================================================
    def crear_pantalla_menu(self):
        self.limpiar_pantalla()
        self.detener_camara()
        self.estado_juego = ""

        tk.Label(self.root, text=f"¡Hola, {self.historial.nombre}! 👋", 
                 font=("Century Gothic", 26, "bold"), fg=COLOR_TITULO, bg=COLOR_FONDO).pack(pady=40)
        
        tk.Label(self.root, text="Selecciona una actividad para comenzar el aprendizaje:", 
                 font=("Century Gothic", 14), fg=COLOR_TEXTO_MAIN, bg=COLOR_FONDO).pack(pady=10)

        btn_a = tk.Button(self.root, text="Modo A: Resolver Operaciones en Pizarra 📐", 
                          font=("Century Gothic", 13, "bold"), bg=COLOR_MODO_A, fg=COLOR_TEXTO_MAIN, 
                          width=45, height=2, relief="flat", command=lambda: self.pedir_intentos(1))
        btn_a.pack(pady=15)

        btn_b = tk.Button(self.root, text="Modo B: Conteo de Objetos en Mesa 🍎", 
                          font=("Century Gothic", 13, "bold"), bg=COLOR_MODO_B, fg=COLOR_TEXTO_MAIN, 
                          width=45, height=2, relief="flat", command=lambda: self.pedir_intentos(2))
        btn_b.pack(pady=15)

        btn_salir = tk.Button(self.root, text="Salir y Guardar mi Historial", 
                              font=("Century Gothic", 12, "bold"), bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, 
                              relief="flat", padx=20, pady=10, command=self.cerrar_todo)
        btn_salir.pack(pady=60)

    def pedir_intentos(self, modo):
        self.limpiar_pantalla()
        self.modo_actual = modo
        
        titulo_texto = "Modo A: Análisis de Pizarra" if modo == 1 else "Modo B: Conteo de Objetos"
        
        tk.Label(self.root, text=titulo_texto, font=("Century Gothic", 24, "bold"), fg=COLOR_TITULO, bg=COLOR_FONDO).pack(pady=40)
        tk.Label(self.root, text="¿Cuántos ejercicios o intentos deseas realizar en esta sesión?", 
                 font=("Century Gothic", 14), fg=COLOR_TEXTO_MAIN, bg=COLOR_FONDO).pack(pady=20)

        self.entry_intentos = tk.Entry(self.root, font=("Century Gothic", 16), justify="center", width=12, relief="solid", bd=1)
        self.entry_intentos.pack(pady=10)
        self.entry_intentos.focus()

        tk.Button(self.root, text="¡Comenzar Actividad!", font=("Century Gothic", 13, "bold"), 
                  bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, relief="flat", padx=25, pady=8, command=self.validar_e_iniciar).pack(pady=25)
                  
        tk.Button(self.root, text="Volver al Menú", font=("Century Gothic", 11), 
                  bg=COLOR_BOTON_NEU, fg=COLOR_TEXTO_MAIN, relief="flat", padx=15, pady=5, command=self.crear_pantalla_menu).pack(pady=10)

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
    # ÁREA DE JUEGO DINÁMICA
    # =========================================================
    def construir_interfaz_juego(self):
        self.limpiar_pantalla()
        
        frame_izq = tk.Frame(self.root, bg=COLOR_FONDO)
        frame_izq.pack(side="left", fill="both", expand=True, padx=30)
        
        self.lbl_contador = tk.Label(frame_izq, text="", font=("Century Gothic", 14, "bold"), fg=COLOR_TITULO, bg=COLOR_FONDO)
        self.lbl_contador.pack(pady=15)
        
        self.lbl_instruccion = tk.Label(frame_izq, text="", font=("Century Gothic", 18, "bold"), 
                                        fg=COLOR_TEXTO_MAIN, bg=COLOR_FONDO, wraplength=400, justify="center")
        self.lbl_instruccion.pack(pady=30)
        
        # Etiqueta que mostrará el resultado o instrucciones dinámicas
        self.lbl_resultado = tk.Label(frame_izq, text="", font=("Century Gothic", 14, "bold"), bg=COLOR_FONDO, wraplength=400, justify="center")
        self.lbl_resultado.pack(pady=20)
        
        self.frame_confirmacion = tk.Frame(frame_izq, bg=COLOR_FONDO)
        tk.Button(self.frame_confirmacion, text="✅ Enviar Captura", font=("Century Gothic", 12, "bold"), 
                  bg=COLOR_BOTON_OK, fg=COLOR_TEXTO_MAIN, relief="flat", padx=15, pady=6, command=self.procesar_captura).pack(side="left", padx=15)
        tk.Button(self.frame_confirmacion, text="🔄 Tomar Otra Foto", font=("Century Gothic", 12, "bold"), 
                  bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, relief="flat", padx=15, pady=6, command=self.cancelar_captura).pack(side="left", padx=15)
        
        frame_der = tk.Frame(self.root, bg="black", bd=2, relief="solid")
        frame_der.pack(side="right", padx=40, pady=40)
        self.lbl_video = tk.Label(frame_der, bg="black")
        self.lbl_video.pack()
        
        self.iniciar_camara()
        
        if self.modo_actual == 1:
            self.siguiente_intento_m1()
        else:
            self.siguiente_intento_m2_mesa()

    def siguiente_intento_m1(self):
        self.estado_juego = "JUGANDO_M1"
        self.video_pausado = False
        self.frame_confirmacion.pack_forget()
        
        self.lbl_contador.config(text=f"Ejercicio {self.intento_actual} de {self.total_intentos}")
        self.ejercicio_str, self.respuesta_esperada = operaciones.generar_operacion()
        
        self.lbl_instruccion.config(text=f"Resuelve en la pizarra:\n\n{self.ejercicio_str} = ?")
        self.lbl_resultado.config(text="Alinea el resultado y presiona ESPACIO.", fg=COLOR_TEXTO_MAIN)
        ModeloA.limpiar_memoria()

    def siguiente_intento_m2_mesa(self):
        self.estado_juego = "M2_MESA"
        self.video_pausado = False
        self.frame_confirmacion.pack_forget()
        
        self.lbl_contador.config(text=f"Conteo {self.intento_actual} de {self.total_intentos}")
        self.lbl_instruccion.config(text="Paso 1:\nColoca los objetos que quieras contar sobre la mesa.")
        self.lbl_resultado.config(text="Presiona ESPACIO para registrar los objetos.", fg=COLOR_TEXTO_MAIN)

    def siguiente_intento_m2_pizarra(self):
        self.estado_juego = "M2_PIZARRA"
        self.video_pausado = False
        self.frame_confirmacion.pack_forget()
        
        self.lbl_instruccion.config(text="Paso 2:\n¡Objetos registrados!\n\nCuenta cuántos pusiste y escribe el número en tu pizarra.")
        self.lbl_resultado.config(text="Encuadra la pizarra y presiona ESPACIO para validar.", fg=COLOR_TEXTO_MAIN)
        ModeloA.limpiar_memoria()

    # =========================================================
    # CÁMARA Y CAPTURAS
    # =========================================================
    def iniciar_camara(self):
        if self.cam is None:
            self.cam = cv2.VideoCapture(1)
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
                                  (ModeloA.X_MAX_ROI, ModeloA.Y_MAX_ROI), (255, 182, 193), 2) # Rectángulo rosado
                    
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
                
                self.lbl_resultado.config(text="¿La imagen se ve bien?", fg=COLOR_TITULO)
                self.frame_confirmacion.pack(pady=10)

    def cancelar_captura(self):
        self.estado_juego = self.estado_memoria
        self.video_pausado = False
        self.frame_confirmacion.pack_forget()
        self.lbl_resultado.config(text="Presiona ESPACIO cuando estés listo.", fg=COLOR_TEXTO_MAIN)

    def procesar_captura(self):
        self.frame_confirmacion.pack_forget()
        self.lbl_resultado.config(text="Pensando... 🤔", fg=COLOR_TEXTO_MAIN)
        self.root.update()
        
        if self.estado_memoria == "JUGANDO_M1":
            self.evaluar_pizarra_m1(self.frame_congelado)
        elif self.estado_memoria == "M2_MESA":
            self.objetos_detectados = ModeloB.contar_objetos(self.frame_congelado)
            self.siguiente_intento_m2_pizarra()
        elif self.estado_memoria == "M2_PIZARRA":
            self.evaluar_pizarra_m2(self.frame_congelado)

    # =========================================================
    # IA, EVALUACIÓN Y FEEDBACK DINÁMICO
    # =========================================================
    def evaluar_pizarra_m1(self, frame):
        texto_yolo = ModeloA.evaluar_frame(frame)
        numeros = re.findall(r'\d+', str(texto_yolo))
        
        if not numeros:
            self.lbl_resultado.config(text="No detecté ningún número. ¡Vuelve a intentarlo!", fg="#C0392B") # Rojo oscuro
            self.cancelar_captura()
            return
            
        respuesta_alumno = int(numeros[-1])
        es_correcto = (respuesta_alumno == self.respuesta_esperada)
        
        # --- AQUÍ ESTÁ EL MENSAJE DINÁMICO QUE PEDISTE ---
        if es_correcto:
            msj_pantalla = f"¡CORRECTO! 🟢\nEscribiste {respuesta_alumno} muy bien."
        else:
            msj_pantalla = f"INCORRECTO 🔴\nTu respuesta fue {respuesta_alumno}, pero el resultado era {self.respuesta_esperada}."
            
        self.notificar_resultado(f"{self.ejercicio_str} = {respuesta_alumno}", es_correcto, msj_pantalla)

    def evaluar_pizarra_m2(self, frame):
        texto_yolo = ModeloA.evaluar_frame(frame)
        numeros = re.findall(r'\d+', str(texto_yolo))
        
        if not numeros:
            self.lbl_resultado.config(text="No detecté ningún número. ¡Vuelve a intentarlo!", fg="#C0392B")
            self.cancelar_captura()
            return
            
        respuesta_alumno = int(numeros[-1])
        es_correcto = (respuesta_alumno == self.objetos_detectados)
        
        # --- AQUÍ ESTÁ EL MENSAJE DINÁMICO PARA EL MODO 2 ---
        if es_correcto:
            msj_pantalla = f"¡CORRECTO! 🟢\nContaste {respuesta_alumno} objetos perfectamente."
        else:
            msj_pantalla = f"INCORRECTO 🔴\nPusiste {respuesta_alumno} pero en realidad habían {self.objetos_detectados} objetos."
            
        self.notificar_resultado(f"Mesa:{self.objetos_detectados} -> Escrito:{respuesta_alumno}", es_correcto, msj_pantalla)

    def notificar_resultado(self, string_registro, es_correcto, msj_pantalla):
        if es_correcto:
            self.uart.correcto()
            self.lbl_resultado.config(text=msj_pantalla, fg="#1E8449") # Verde oscuro visible en fondo pastel
        else:
            self.uart.incorrecto()
            self.lbl_resultado.config(text=msj_pantalla, fg="#C0392B") # Rojo oscuro visible en fondo pastel
            
        self.historial.agregar_resultado(string_registro, "Cámara", es_correcto)
        
        if self.intento_actual < self.total_intentos:
            self.intento_actual += 1
            # Aumenté el tiempo a 3.5s para que el niño alcance a leer la retroalimentación
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
        self.limpiar_pantalla()
        self.detener_camara()
        
        tk.Label(self.root, text="¡Actividad Concluida! 🎉", 
                 font=("Century Gothic", 26, "bold"), fg=COLOR_TITULO, bg=COLOR_FONDO).pack(pady=40)
        
        porcentaje = self.historial.puntaje()
        tk.Label(self.root, text=f"Respuestas Correctas: {self.historial.correctas}", font=("Century Gothic", 16), fg="#1E8449", bg=COLOR_FONDO).pack(pady=5)
        tk.Label(self.root, text=f"Respuestas Incorrectas: {self.historial.incorrectas}", font=("Century Gothic", 16), fg="#C0392B", bg=COLOR_FONDO).pack(pady=5)
        tk.Label(self.root, text=f"Puntaje Final: {porcentaje}%", font=("Century Gothic", 20, "bold"), fg=COLOR_MODO_A, bg=COLOR_FONDO).pack(pady=20)
        
        tk.Button(self.root, text="Volver a Jugar este Modo", font=("Century Gothic", 12, "bold"), 
                  bg=COLOR_MODO_A, fg=COLOR_TEXTO_MAIN, width=30, relief="flat", command=lambda: self.pedir_intentos(self.modo_actual)).pack(pady=10)
                  
        tk.Button(self.root, text="Ir al Menú de Selección", font=("Century Gothic", 12, "bold"), 
                  bg=COLOR_MODO_B, fg=COLOR_TEXTO_MAIN, width=30, relief="flat", command=self.crear_pantalla_menu).pack(pady=10)
                  
        tk.Button(self.root, text="Salir del Sistema", font=("Century Gothic", 11), 
                  bg=COLOR_BOTON_ERR, fg=COLOR_TEXTO_MAIN, width=20, relief="flat", command=self.cerrar_todo).pack(pady=25)

    def cerrar_todo(self):
        if self.historial:
            self.historial.finalizar_sesion()
        self.uart.cerrar()
        self.detener_camara()
        self.root.quit()

if __name__ == "__main__":
    access = AccessWindow()