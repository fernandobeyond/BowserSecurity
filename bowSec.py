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
import smtplib
import ssl
from email.message import EmailMessage
from twilio.rest import Client
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

def check_env_vars():
    """Valida que todas las variables de entorno necesarias estén definidas."""
    required = [
        "EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECEIVER",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
        "SMS_RECEIVER_NUMBERS",  # lista separada por comas: +5197954631,+51940317018,...
        "LOGIN_USER", "LOGIN_PASS"
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        error_msg = f"Faltan las siguientes variables de entorno: {', '.join(missing)}"
        logging.error(error_msg)
        messagebox.showerror("Error de Configuración", error_msg)
        exit(1)

check_env_vars()

# Configuración desde .env
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
SMS_RECEIVER_NUMBERS = [n.strip() for n in os.getenv("SMS_RECEIVER_NUMBERS").split(",") if n.strip()]

LOGIN_USER = os.getenv("LOGIN_USER")
LOGIN_PASS = os.getenv("LOGIN_PASS")

AGGRESSIVE_CLASSES = ['knife', 'gun']
CAMERA_URL = os.getenv("CAMERA_URL", 'https://raspberrybowser.ngrok.app/video')
ALARM_SOUND_PATH = os.getenv("ALARM_SOUND_PATH", 'media/alarm.mp3')

# Inicializar mixer de pygame
mixer.init()

# ----------------------------------------------------------------------
# Clase para notificaciones (correo y SMS) en hilos separados
# ----------------------------------------------------------------------
class Notifier:
    @staticmethod
    def send_email(subject, body):
        def _send():
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
                    smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                    smtp.send_message(msg)
                logging.info("Correo enviado exitosamente.")
            except Exception as e:
                logging.error(f"Error al enviar correo: {e}")
        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

    @staticmethod
    def send_sms(body):
        def _send():
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                for number in SMS_RECEIVER_NUMBERS:
                    message = client.messages.create(
                        to=number,
                        from_=TWILIO_PHONE_NUMBER,
                        body=body
                    )
                    logging.info(f"SMS enviado a {number}. SID: {message.sid}")
            except Exception as e:
                logging.error(f"Error al enviar SMS: {e}")
        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

# ----------------------------------------------------------------------
# Pantalla de inicio de sesión
# ----------------------------------------------------------------------
class LoginScreen:
    def __init__(self, master):
        self.master = master
        master.title("Iniciar Sesión - BowserSecurity")
        master.geometry("400x250")
        master.resizable(False, False)
        master.configure(bg="#736fb6")

        self.center_window(master, 400, 250)

        self.attempts = 0
        self.max_attempts = 3

        frame = tk.Frame(master, bg="#ffffff", bd=2, relief="groove")
        frame.pack(pady=30, padx=30, fill="both", expand=True)

        tk.Label(frame, text="Acceso al Sistema", font=("Inter", 16, "bold"), bg="#ffffff", fg="#333333").pack(pady=(20, 15))
        tk.Label(frame, text="Usuario:", font=("Inter", 10), bg="#ffffff").pack(anchor="w", padx=40)
        self.entry_user = tk.Entry(frame, width=30, font=("Inter", 10))
        self.entry_user.pack(pady=5, padx=40)
        self.entry_user.focus_set()

        tk.Label(frame, text="Contraseña:", font=("Inter", 10), bg="#ffffff").pack(anchor="w", padx=40)
        self.entry_pass = tk.Entry(frame, show="*", width=30, font=("Inter", 10))
        self.entry_pass.pack(pady=5, padx=40)

        tk.Button(frame, text="Ingresar", command=self.check_login, font=("Inter", 10, "bold"),
                  bg="#4CAF50", fg="white", activebackground="#45a049", relief="raised", bd=2, cursor="hand2").pack(pady=(15, 20))

        master.bind('<Return>', lambda e: self.check_login())

    def center_window(self, window, width, height):
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f'{width}x{height}+{x}+{y}')

    def check_login(self):
        user = self.entry_user.get()
        pwd = self.entry_pass.get()

        if user == LOGIN_USER and pwd == LOGIN_PASS:
            # Enviar notificaciones de bienvenida en segundo plano
            Notifier.send_email("Bienvenido a BowserSecurity", "Has iniciado sesión correctamente.")
            Notifier.send_sms("Bienvenido a BowserSecurity")

            self.master.destroy()
            root = tk.Tk()
            MainApplication(root)
            root.mainloop()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            if remaining <= 0:
                messagebox.showerror("Inicio de Sesión Fallido", "Demasiados intentos fallidos. Saliendo.")
                self.master.destroy()
            else:
                messagebox.showwarning("Inicio de Sesión Fallido", f"Credenciales incorrectas. Intentos restantes: {remaining}")
                self.entry_user.delete(0, tk.END)
                self.entry_pass.delete(0, tk.END)
                self.entry_user.focus_set()

# ----------------------------------------------------------------------
# Aplicación principal
# ----------------------------------------------------------------------
class MainApplication:
    def __init__(self, master):
        self.master = master
        master.title("BowserSecurity FIEE v1.3")
        master.geometry("1200x800")
        master.state('zoomed')
        master.configure(bg="#aaccff")

        # Cargar modelo YOLO como atributo de clase
        self.model = None
        try:
            self.model = YOLO("media/yolov8n.pt")
        except Exception as e:
            messagebox.showerror("Error de Modelo", f"No se pudo cargar YOLO: {e}")
            master.destroy()
            return

        self.cap = None
        self.video_thread = None
        self.stop_event = threading.Event()
        self.is_aggressive_detected = False
        self.alarm_playing = False
        self.current_processed_frame = None
        self.video_width, self.video_height = 800, 600

        self.setup_ui()
        self.start_video_stream()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Cargar sonido de alarma
        if os.path.exists(ALARM_SOUND_PATH):
            try:
                mixer.music.load(ALARM_SOUND_PATH)
            except Exception as e:
                messagebox.showerror("Error de Sonido", f"No se pudo cargar el sonido: {e}")
        else:
            logging.warning(f"Archivo de alarma no encontrado: {ALARM_SOUND_PATH}")

    def setup_ui(self):
        # Barra superior
        top = tk.Frame(self.master, bg="#2c3e50", height=60)
        top.pack(fill="x", side="top")
        tk.Label(top, text="BowserSecurity FIEE v1.3 - Grupo 5 - BMA15", font=("Inter", 20, "bold"), fg="white", bg="#2c3e50").pack(pady=(10, 0))
        tk.Label(top, text="Fernando Flores - Bryan Palomino - Angel Mejia", font=("Inter", 10), fg="white", bg="#2c3e50").pack(pady=(0, 10))

        main = tk.Frame(self.master, bg="#f0f2f5")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)

        # Panel de video
        left = tk.Frame(main, bg="#ffffff", bd=2, relief="groove")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        self.video_label = tk.Label(left, bg="#eeeeee")
        self.video_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.video_label.bind("<Configure>", self.on_video_label_resize)

        # Panel de control
        right = tk.Frame(main, bg="#ffffff", bd=2, relief="groove", width=350)
        right.grid(row=0, column=1, sticky="nsew")
        right.pack_propagate(False)

        btn_frame = tk.LabelFrame(right, text="Controles", font=("Inter", 12, "bold"), bg="#ffffff", fg="#333333", padx=15, pady=15)
        btn_frame.pack(pady=20, padx=15, fill="x")

        btn_style = {"font": ("Inter", 11, "bold"), "bg": "#3498db", "fg": "white", "activebackground": "#2980b9", "relief": "raised", "bd": 2, "cursor": "hand2"}

        tk.Button(btn_frame, text="Reconectar Video", command=self.reconnect_video, **btn_style).pack(pady=7, fill="x")
        tk.Button(btn_frame, text="Capturar Imagen", command=self.capture_image, **btn_style).pack(pady=7, fill="x")
        tk.Button(btn_frame, text="Detener Alarma", command=self.stop_alarm, font=("Inter", 11, "bold"), bg="#f39c12", fg="white", activebackground="#e67e22", relief="raised", bd=2, cursor="hand2").pack(pady=7, fill="x")
        tk.Button(btn_frame, text="Emergencia", command=self.show_emergency_numbers, font=("Inter", 11, "bold"), bg="#e74c3c", fg="white", activebackground="#c0392b", relief="raised", bd=2, cursor="hand2").pack(pady=7, fill="x")

        # Registro de incidentes
        log_frame = tk.LabelFrame(right, text="Registro de Incidentes", font=("Inter", 12, "bold"), bg="#ffffff", fg="#333333", padx=15, pady=10)
        log_frame.pack(pady=20, padx=15, fill="both", expand=True)

        self.incident_log = Text(log_frame, wrap="word", font=("Inter", 10), bg="#ecf0f1")
        scrollbar = Scrollbar(log_frame, command=self.incident_log.yview)
        self.incident_log.configure(yscrollcommand=scrollbar.set)
        self.incident_log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def on_video_label_resize(self, event):
        self.video_width = event.width
        self.video_height = event.height

    def start_video_stream(self):
        if self.video_thread and self.video_thread.is_alive():
            self.stop_event.set()
            self.video_thread.join(timeout=1)
        self.stop_event.clear()

        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(CAMERA_URL)
        if not self.cap.isOpened():
            messagebox.showerror("Error de Video", f"No se pudo abrir: {CAMERA_URL}")
            self.video_label.config(image=None)
            return

        self.video_thread = threading.Thread(target=self.video_processing_loop, daemon=True)
        self.video_thread.start()

    def reconnect_video(self):
        messagebox.showinfo("Reconexión", "Reiniciando conexión de video...")
        self.start_video_stream()

    def video_processing_loop(self):
        retry_delay = 2
        max_delay = 30
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                logging.warning("Frame no recibido. Reintentando en %d seg...", retry_delay)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
                self.cap.release()
                self.cap = cv2.VideoCapture(CAMERA_URL)
                if not self.cap.isOpened():
                    self.master.after(0, lambda: self.video_label.config(image=None))
                    self.master.after(0, lambda: messagebox.showerror("Error", "Transmisión perdida. Use Reconectar."))
                    break
                continue
            retry_delay = 2  # resetear

            processed, agg_count, vic_count = self.process_frame(frame)
            self.current_processed_frame = processed.copy()

            # Lógica de alarma y notificaciones
            if agg_count > 0:
                if not self.is_aggressive_detected:
                    self.is_aggressive_detected = True
                    msg = f"Agresores: {agg_count}, Víctimas: {vic_count}."
                    self.log_incident(msg)
                    # Notificaciones asíncronas
                    Notifier.send_email("ALERTA: Amenaza detectada", msg)
                    Notifier.send_sms(f"ALERTA: {msg}")
                    self.play_alarm()
            else:
                if self.is_aggressive_detected:
                    self.is_aggressive_detected = False
                    self.stop_alarm()

            # Redimensionar y mostrar
            h, w = processed.shape[:2]
            if self.video_width > 0 and self.video_height > 0:
                ratio = min(self.video_width / w, self.video_height / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                resized = cv2.resize(processed, (new_w, new_h))
            else:
                resized = processed

            img = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.master.after(0, self._update_video_label, imgtk)

        if self.cap:
            self.cap.release()

    def _update_video_label(self, imgtk):
        self.video_label.imgtk = imgtk
        self.video_label.config(image=imgtk)

    def process_frame(self, frame):
        results = self.model(frame, conf=0.1)[0]
        people = []
        weapons = []
        for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
            x1, y1, x2, y2 = map(int, box)
            label = self.model.names[int(cls)]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if label == 'person':
                people.append({'box': (x1, y1, x2, y2), 'center': (cx, cy)})
            elif label in AGGRESSIVE_CLASSES:
                weapons.append({'box': (x1, y1, x2, y2), 'center': (cx, cy), 'label': label})

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

            # Dibujar arma
            x1, y1, x2, y2 = weapon['box']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, weapon['label'].upper(), (x1, y2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        agg_count = 0
        vic_count = 0
        for i, person in enumerate(people):
            x1, y1, x2, y2 = person['box']
            if i in aggressive_indices:
                text = "Persona Agresiva"
                color = (0, 0, 255)
                agg_count += 1
            else:
                if aggressive_indices:
                    text = "Victima"
                    color = (0, 255, 255)
                    vic_count += 1
                else:
                    text = "Persona"
                    color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return frame, agg_count, vic_count

    def capture_image(self):
        if self.current_processed_frame is not None and self.current_processed_frame.size > 0:
            os.makedirs("capturas", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"capturas/captura_{ts}.png"
            cv2.imwrite(path, self.current_processed_frame)
            messagebox.showinfo("Captura", f"Guardada como {path}")
        else:
            messagebox.showwarning("Captura", "No hay frame disponible.")

    def show_emergency_numbers(self):
        win = tk.Toplevel(self.master)
        win.title("Números de Emergencia - Perú")
        win.geometry("350x200+{}+{}".format(
            self.master.winfo_x() + self.master.winfo_width()//2 - 175,
            self.master.winfo_y() + self.master.winfo_height()//2 - 100))
        win.resizable(False, False)
        win.transient(self.master)
        win.grab_set()

        tk.Label(win, text="Números de Emergencia", font=("Inter", 14, "bold"), bg="#f8f8f8").pack(pady=15)
        for svc, num in [("Policía", "105"), ("Defensa Civil", "115"), ("Bomberos", "116")]:
            tk.Label(win, text=f"{svc}: {num}", font=("Inter", 11), bg="#f8f8f8").pack(anchor="w", padx=40, pady=2)
        tk.Button(win, text="Cerrar", command=win.destroy, font=("Inter", 10, "bold"), bg="#95a5a6", fg="white").pack(pady=15)

    def play_alarm(self):
        if not self.alarm_playing and os.path.exists(ALARM_SOUND_PATH):
            mixer.music.play(-1)
            self.alarm_playing = True
            logging.info("Alarma activada")

    def stop_alarm(self):
        if self.alarm_playing:
            mixer.music.stop()
            self.alarm_playing = False
            logging.info("Alarma detenida")

    def log_incident(self, extra=""):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] INCIDENTE: {extra}\n"
        self.incident_log.insert(tk.END, msg)
        self.incident_log.see(tk.END)

    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Está seguro de que desea salir?"):
            self.stop_event.set()
            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=2)
            self.stop_alarm()
            if self.cap:
                self.cap.release()
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    LoginScreen(root)
    root.mainloop()