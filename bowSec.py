import tkinter as tk
from tkinter import messagebox, Text, Scrollbar
from PIL import Image, ImageTk
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import time
from dotenv import load_dotenv
from datetime import datetime
import os
from pygame import mixer

# Importaciones para el envío de correo electrónico
import smtplib
import ssl
from email.message import EmailMessage

# Importación para el envío de SMS (Twilio)
from twilio.rest import Client

# Inicializar mixer de pygame para reproducir el audio
mixer.init()

load_dotenv()  # Carga las variables desde el archivo .env

# Cargar el modelo YOLO
try:
    model = YOLO("yolov8n.pt")
except Exception as e:
    messagebox.showerror("Error de Modelo", f"No se pudo cargar el modelo YOLOv8n.pt: {e}\nAsegúrate de que 'yolov8n.pt' esté en el mismo directorio.")
    exit()

# Se definen las clases consideradas agresivas
AGGRESSIVE_CLASSES = ['knife', 'gun']

# URL de la cámara (usando ngrok)
CAMERA_URL = 'https://raspberrybowser.ngrok.app/video'

ALARM_SOUND_PATH = 'alarm.mp3'

EMAIL_SENDER = os.getenv("EMAIL_SENDER")     # Se ingresa el correo
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Se ingresa la contraseña de aplicación
EMAIL_RECEIVER = "f.flores.q@uni.pe"    # Correo de destino

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")    # ACCOUNT_SID del Twilio
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")      # AUTH_TOKEN del Twilio
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_AUTH_TOKEN")     # Numero publico del Twilio
SMS_RECEIVER_NUMBER = ["NUMBERS"]

# Clase para la pantalla de inicio de sesión
class LoginScreen:
    def __init__(self, master):
        self.master = master
        master.title("Iniciar Sesión a BowserSecurity")
        master.geometry("400x250")
        master.resizable(False, False)
        master.config(bg="#736fb6")

        # Centrar la ventana de inicio de sesión
        self.center_window(master, 400, 250)

        self.username = "Bowser"
        self.password = "12345678"
        self.attempts = 0
        self.max_attempts = 3

        # Frame principal para el contenido de inicio de sesión
        self.login_frame = tk.Frame(master, bg="#ffffff", bd=2, relief="groove")
        self.login_frame.pack(pady=30, padx=30, fill="both", expand=True)

        # Título
        self.title_label = tk.Label(self.login_frame, text="Acceso al Sistema", font=("Inter", 16, "bold"), bg="#ffffff", fg="#333333")
        self.title_label.pack(pady=(20, 15))

        # Etiquetas y campos de entrada
        self.username_label = tk.Label(self.login_frame, text="Usuario:", font=("Inter", 10), bg="#ffffff")
        self.username_label.pack(anchor="w", padx=40)
        self.username_entry = tk.Entry(self.login_frame, width=30, font=("Inter", 10), bd=1, relief="solid")
        self.username_entry.pack(pady=5, padx=40)
        self.username_entry.focus_set()

        self.password_label = tk.Label(self.login_frame, text="Contraseña:", font=("Inter", 10), bg="#ffffff")
        self.password_label.pack(anchor="w", padx=40)
        self.password_entry = tk.Entry(self.login_frame, show="*", width=30, font=("Inter", 10), bd=1, relief="solid")
        self.password_entry.pack(pady=5, padx=40)

        # Botón de inicio de sesión
        self.login_button = tk.Button(self.login_frame, text="Ingresar", command=self.check_login, font=("Inter", 10, "bold"), bg="#4CAF50", fg="white", activebackground="#45a049", relief="raised", bd=2, cursor="hand2")
        self.login_button.pack(pady=(15, 20))

        # Permitir presionar Enter para iniciar sesión
        self.master.bind('<Return>', lambda event: self.check_login())

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    # Verifica las credenciales de inicio de sesión
    def check_login(self):
        entered_username = self.username_entry.get()
        entered_password = self.password_entry.get()

        if entered_username == self.username and entered_password == self.password:
            self.master.destroy()
            root = tk.Tk()
            app = MainApplication(root)
            root.mainloop()
        else:
            self.attempts += 1
            if self.attempts >= self.max_attempts:
                messagebox.showerror("Inicio de Sesión Fallido", "Demasiados intentos fallidos. Saliendo de la aplicación.")
                self.master.destroy()
            else:
                messagebox.showwarning("Inicio de Sesión Fallido", f"Usuario o contraseña incorrectos. Intentos restantes: {self.max_attempts - self.attempts}")
                self.password_entry.delete(0, tk.END) # Limpiar campo de contraseña
                self.username_entry.delete(0, tk.END) # Limpiar campo de usuario
                self.username_entry.focus_set() # Volver a poner el foco en el campo de usuario

# Clase principal para la interfaz de la aplicación
class MainApplication:
    def __init__(self, master):
        self.master = master
        master.title("BowserSecurity FIEE v1.2")
        master.geometry("1200x800")
        master.state('zoomed')
        master.config(bg="#aaccff")

        self.cap = None
        self.video_thread = None
        self.stop_event = threading.Event()
        self.is_aggressive_detected = False
        self.alarm_playing = False
        self.last_aggressive_detection_time = None
        self.current_processed_frame = None # Nueva variable para almacenar el último frame procesado

        # Inicializar el tamaño del video para evitar que sea cero al principio
        self.video_width = 800  # Ancho inicial razonable
        self.video_height = 600 # Alto inicial razonable

        # Configurar la interfaz principal
        self.setup_ui()

        # Inicio de la transmisión de video automáticamente al iniciar la aplicación
        self.start_video_stream()

        # Manejar el cierre de la ventana
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Cargar el sonido de la alarma una vez
        if os.path.exists(ALARM_SOUND_PATH):
            try:
                mixer.music.load(ALARM_SOUND_PATH)
            except Exception as e:
                messagebox.showerror("Error de Sonido", f"No se pudo cargar el archivo de sonido de la alarma: {e}\nAsegúrate de que el archivo es válido y la ruta es correcta.")
        else:
            messagebox.showwarning("Archivo de Sonido no Encontrado", f"El archivo de alarma '{ALARM_SOUND_PATH}' no se encontró. La alarma no sonará.")

    # Configura los elementos de la interfaz de usuario principal
    def setup_ui(self):
        top_frame = tk.Frame(self.master, bg="#2c3e50", height=60)
        top_frame.pack(fill="x", side="top")
        title_label = tk.Label(top_frame, text="BowserSecurity FIEE v1.2 - Grupo 5 - BMA15", font=("Inter", 20, "bold"), fg="white", bg="#2c3e50")
        title_label.pack(pady=(10, 0))

        group_label = tk.Label(top_frame, text="Elaborado por: Fernando Flores - Bryan Palomino - Angel Mejia", font=("Inter", 10), fg="white", bg="#2c3e50")
        group_label.pack(pady=(0, 10))

        # Frame principal
        main_frame = tk.Frame(self.master, bg="#f0f2f5")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Configurar grid para main_frame
        main_frame.grid_rowconfigure(0, weight=1) 
        main_frame.grid_columnconfigure(0, weight=1) 
        main_frame.grid_columnconfigure(1, weight=0)

        # Frame izquierdo para el video
        left_frame = tk.Frame(main_frame, bg="#ffffff", bd=2, relief="groove")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        self.video_label = tk.Label(left_frame, bg="#eeeeee")
        self.video_label.pack(fill="both", expand=True, padx=10, pady=10)

        self.video_label.bind("<Configure>", self.on_video_label_resize)

        # Frame derecho para controles y log
        right_frame = tk.Frame(main_frame, bg="#ffffff", bd=2, relief="groove", width=350)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        right_frame.pack_propagate(False)

        # Sección de botones
        buttons_frame = tk.LabelFrame(right_frame, text="Controles", font=("Inter", 12, "bold"), bg="#ffffff", fg="#333333", padx=15, pady=15)
        buttons_frame.pack(pady=20, padx=15, fill="x")

        button_font = ("Inter", 11, "bold")
        button_bg = "#3498db"
        button_fg = "white"
        button_active_bg = "#2980b9"

        self.reconnect_button = tk.Button(buttons_frame, text="Reconectar Video", command=self.reconnect_video, font=button_font, bg=button_bg, fg=button_fg, activebackground=button_active_bg, relief="raised", bd=2, cursor="hand2")
        self.reconnect_button.pack(pady=7, fill="x")

        self.capture_button = tk.Button(buttons_frame, text="Capturar Imagen", command=self.capture_image, font=button_font, bg=button_bg, fg=button_fg, activebackground=button_active_bg, relief="raised", bd=2, cursor="hand2")
        self.capture_button.pack(pady=7, fill="x")

        self.alert_button = tk.Button(buttons_frame, text="Mostrar Números de Emergencia", command=self.show_emergency_numbers, font=button_font, bg="#e74c3c", fg=button_fg, activebackground="#c0392b", relief="raised", bd=2, cursor="hand2")
        self.alert_button.pack(pady=7, fill="x")

        # Sección de registro de incidentes
        log_frame = tk.LabelFrame(right_frame, text="Registro de Incidentes", font=("Inter", 12, "bold"), bg="#ffffff", fg="#333333", padx=15, pady=10)
        log_frame.pack(pady=20, padx=15, fill="both", expand=True)

        self.incident_log = Text(log_frame, wrap="word", font=("Inter", 10), bg="#ecf0f1", fg="#2c3e50", bd=1, relief="solid")
        self.incident_log.pack(side="left", fill="both", expand=True)

        log_scrollbar = Scrollbar(log_frame, command=self.incident_log.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.incident_log.config(yscrollcommand=log_scrollbar.set)

    def on_video_label_resize(self, event):
        self.video_width = event.width
        self.video_height = event.height

    def start_video_stream(self):
        if self.video_thread and self.video_thread.is_alive():
            self.stop_event.set()
            self.video_thread.join(timeout=1)
            self.stop_event.clear()

        self.cap = cv2.VideoCapture(CAMERA_URL)
        if not self.cap.isOpened():
            messagebox.showerror("Error de Video", f"No se pudo abrir la URL del video: {CAMERA_URL}. Por favor, verifica la URL o la conexión.")
            self.video_label.config(image=None)
            return

        self.video_thread = threading.Thread(target=self.video_processing_loop)
        self.video_thread.daemon = True
        self.video_thread.start()

    # Detiene el hilo actual y reinicia la transmisión de video
    def reconnect_video(self):
        messagebox.showinfo("Reconectar Video", "Intentando reconectar el video...")
        self.start_video_stream()

    # Envía una alerta por correo electrónico
    def send_email_alert(self, message_body):
        msg = EmailMessage()
        msg.set_content(f"Amenaza detectada: {message_body}")
        msg['Subject'] = "ALERTA DE SEGURIDAD: AMENAZA DETECTADA"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
                smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                smtp.send_message(msg)
            print("Alerta por correo electrónico enviada exitosamente.")
        except Exception as e:
            print(f"Error al enviar correo electrónico: {e}")
            messagebox.showerror("Error de Correo", f"No se pudo enviar el correo electrónico de alerta: {e}")

    # Envía una alerta por SMS usando Twilio
    def send_sms_alert(self, message_body):
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            for number in SMS_RECEIVER_NUMBER: # Iterar sobre la lista de números
                message = client.messages.create(
                    to=number,  # Envía a cada número en la lista
                    from_=TWILIO_PHONE_NUMBER,
                    body=f"ALERTA: Amenaza detectada. {message_body}"
                )
                print(f"Alerta SMS enviada exitosamente a {number}. SID del mensaje: {message.sid}")
        except Exception as e:
            print(f"Error al enviar SMS: {e}")
            messagebox.showerror("Error de SMS", f"No se pudo enviar el SMS de alerta: {e}\nPor favor, verifica tus credenciales y números de Twilio.")
    
    def video_processing_loop(self):
        while self.video_width == 0 or self.video_height == 0:
            time.sleep(0.1)

        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                print("No se pudo recibir el frame. Intentando reconectar...")
                time.sleep(2)
                self.cap = cv2.VideoCapture(CAMERA_URL)
                if not self.cap.isOpened():
                    self.master.after(0, lambda: self.video_label.config(image=None))
                    self.master.after(0, lambda: messagebox.showerror("Error de Conexión", "La transmisión de video se ha perdido. Por favor, haz clic en 'Reconectar Video'."))
                    break
                continue

            processed_frame, aggressive_people_count, victim_count = self.process_frame(frame)
            self.current_processed_frame = processed_frame.copy()

            # Controlar la alarma y enviar notificación basado en la detección de personas agresivas
            if aggressive_people_count > 0:
                if not self.is_aggressive_detected:
                    self.is_aggressive_detected = True
                    self.last_aggressive_detection_time = datetime.now()
                    log_message = f"Agresores: {aggressive_people_count}, Víctimas Cercanas: {victim_count}."
                    self.log_incident(aggressive_people_count, victim_count)
                    # Enviar correo y SMS cuando se detecta por primera vez
                    self.send_email_alert(log_message)
                    self.send_sms_alert(log_message)
                    self.play_alarm()
            else:
                if self.is_aggressive_detected:
                    self.is_aggressive_detected = False
                    self.stop_alarm()

            # Redimensionar el frame para ajustarse al label
            h, w, _ = processed_frame.shape
            if self.video_width > 0 and self.video_height > 0:
                ratio = min(self.video_width / w, self.video_height / h)
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                resized_frame = cv2.resize(processed_frame, (new_w, new_h))
            else:
                resized_frame = processed_frame

            img = Image.fromarray(cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB))
            img_tk = ImageTk.PhotoImage(image=img)

            self.video_label.image_tk = img_tk
            self.master.after(0, lambda: self.video_label.config(image=img_tk)) # Actualizar la imagen en el label

        # Cuando el bucle termina, liberar el objeto de captura
        if self.cap:
            self.cap.release()

    # Realiza la detección de objetos con YOLO y dibuja los resultados
    def process_frame(self, frame):
        results = model(frame, conf=0.1)[0]

        people = []
        weapons = []
        aggressive_people_count = 0
        victim_count = 0

        for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
            x1, y1, x2, y2 = map(int, box)
            label = model.names[int(cls)]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            if label == 'person':
                people.append({'box': (x1, y1, x2, y2), 'center': (cx, cy)})
            elif label in AGGRESSIVE_CLASSES:
                weapons.append({'box': (x1, y1, x2, y2), 'center': (cx, cy), 'label': label})

        # Asignamos a la persona como agresiva si está más cerca a un arma)
        aggressive_indices = set()
        for weapon in weapons:
            min_dist = float('inf')
            closest_idx = -1
            for i, person in enumerate(people):
                dist = np.linalg.norm(np.array(weapon['center']) - np.array(person['center']))
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            if closest_idx != -1:
                aggressive_indices.add(closest_idx)

            # Dibujar el arma
            x1, y1, x2, y2 = weapon['box']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2) # Rojo
            cv2.putText(frame, weapon['label'].upper(), (x1, y2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        # Dibujar personas con etiquetas según cercanía
        for i, person in enumerate(people):
            x1, y1, x2, y2 = person['box']
            if i in aggressive_indices:
                text = "Persona Agresiva"
                color = (0, 0, 255)
                aggressive_people_count += 1
            else:
                if aggressive_indices:
                    text = "Víctima"
                    color = (0, 255, 255)
                    victim_count += 1
                else:
                    text = "Persona"
                    color = (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)

        return frame, aggressive_people_count, victim_count

    def capture_image(self):
        if self.current_processed_frame is not None:
            if self.current_processed_frame.shape[0] > 0 and self.current_processed_frame.shape[1] > 0:
                try:
                    captures_dir = "capturas"
                    os.makedirs(captures_dir, exist_ok=True)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(captures_dir, f"captura_{timestamp}.png")
                    cv2.imwrite(filename, self.current_processed_frame)
                    messagebox.showinfo("Captura de Imagen", f"Imagen guardada como {filename}")
                except Exception as e:
                    messagebox.showerror("Error de Captura", f"No se pudo guardar la imagen: {e}\nEsto podría deberse a un frame corrupto o permisos de escritura.")
            else:
                messagebox.showwarning("Captura de Imagen", "El frame procesado actual no es válido o está vacío.")
        else:
            messagebox.showwarning("Captura de Imagen", "No hay un frame procesado disponible para capturar. Asegúrate de que el video esté activo.")

    # Muestra los números de emergencia en una nueva ventana
    def show_emergency_numbers(self):
        emergency_window = tk.Toplevel(self.master)
        emergency_window.title("Números de Emergencia - Perú")
        emergency_window.geometry("350x200")
        emergency_window.resizable(False, False)
        emergency_window.config(bg="#f8f8f8")
        emergency_window.transient(self.master)
        emergency_window.grab_set()

        # Centrar la ventana de emergencia
        self.center_toplevel_window(emergency_window, 350, 200)

        label_title = tk.Label(emergency_window, text="Números de Emergencia", font=("Inter", 14, "bold"), bg="#f8f8f8", fg="#2c3e50")
        label_title.pack(pady=15)

        numbers = {
            "Policía Nacional del Perú": "105",
            "Defensa Civil": "115",
            "Bomberos": "116"
        }

        for service, number in numbers.items():
            tk.Label(emergency_window, text=f"{service}: {number}", font=("Inter", 11), bg="#f8f8f8", fg="#333333").pack(anchor="w", padx=40, pady=2)

        close_button = tk.Button(emergency_window, text="Cerrar", command=emergency_window.destroy, font=("Inter", 10, "bold"), bg="#95a5a6", fg="white", activebackground="#7f8c8d", relief="raised", bd=2, cursor="hand2")
        close_button.pack(pady=15)

    def center_toplevel_window(self, window, width, height):
        self.master.update_idletasks()
        x_parent = self.master.winfo_x() + self.master.winfo_width() // 2
        y_parent = self.master.winfo_y() + self.master.winfo_height() // 2
        x = x_parent - (width // 2)
        y = y_parent - (height // 2)
        window.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    # Reproduce el sonido de la alarma
    def play_alarm(self):
        if not self.alarm_playing and os.path.exists(ALARM_SOUND_PATH):
            try:
                mixer.music.play(-1)
                self.alarm_playing = True
                print("Alarma: ON")
            except Exception as e:
                print(f"Error al reproducir la alarma: {e}")
        elif not os.path.exists(ALARM_SOUND_PATH):
            print(f"Advertencia: El archivo de alarma '{ALARM_SOUND_PATH}' no existe. No se puede reproducir.")

    def stop_alarm(self):
        if self.alarm_playing:
            mixer.music.stop()
            self.alarm_playing = False
            print("Alarma: OFF")

    def log_incident(self, aggressive_count, victim_count):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{current_time}] - INCIDENTE: Persona(s) Agresiva(s) detectada(s). "
        log_message += f"Agresores: {aggressive_count}, Víctimas Cercanas: {victim_count}.\n"
        self.incident_log.insert(tk.END, log_message)
        self.incident_log.see(tk.END)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Estás seguro de que quieres salir?"):
            self.stop_event.set()
            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=2)
            self.stop_alarm()
            if self.cap:
                self.cap.release()
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    login_app = LoginScreen(root)
    root.mainloop()