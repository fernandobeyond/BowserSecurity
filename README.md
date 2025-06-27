# 🛡 BowserSecurity: Detección Inteligente de Armas

**Proyecto Final - Programación Orientada a Objetos**  
Facultad de Ingeniería Eléctrica y Electrónica – Universidad Nacional de Ingeniería  
Autores:  
- Fernando Flores Quiliche – 20247516A  
- Bryan Raúl Palomino Guzmán – 20240549A  
- Ángel Fernando Mejía Estrada – 20242161K  
Supervisor: Yury Oscar Tello  
📅 Lima, 27 de junio de 2025  

---

## 📌 Descripción del Proyecto

**BowserSecurity** es un sistema de videovigilancia inteligente y autónomo diseñado para detectar amenazas en tiempo real, especialmente armas, a través de visión por computadora y dispositivos IoT. Utiliza una Raspberry Pi como nodo de captura y un servidor Python como unidad de análisis. El modelo de detección está basado en **YOLOv8**, permitiendo identificar comportamientos sospechosos y emitir alertas inmediatas (sonido, SMS, correo).

---

## 🎯 Objetivos

### Objetivo General
Desarrollar un sistema de videovigilancia inteligente con Raspberry Pi, visión computacional y modelo IA entrenado para detectar acciones sospechosas, generando alertas automáticas en tiempo real mediante Python y Programación Orientada a Objetos.

### Objetivos Específicos
- Configurar una Raspberry Pi con cámara como nodo autónomo de monitoreo.
- Implementar software modular en Python usando POO.
- Integrar un modelo YOLO optimizado para detectar amenazas visuales.
- Procesar video en tiempo real localmente y emitir alertas inmediatas.
- Registrar eventos y permitir el uso de alarmas o notificaciones.
- Validar el sistema en escenarios reales como hogares o tiendas.

---

## 🛠️ Tecnologías Utilizadas

- **Hardware:** Raspberry Pi Pico W, cámara USB
- **Software:** Python 3.10+, Tkinter, OpenCV, YOLOv8, Twilio API, smtplib, dotenv
- **Modelos IA:** YOLOv8 (Ultralytics)
- **Protocolos:** HTTP / Socket / SMTP / TLS
- **Arquitectura:** Cliente (Raspberry Pi) – Servidor (procesamiento centralizado)

---

## 🖼️ Arquitectura del Sistema

El sistema se divide en dos partes:

### 1. 📷 Nodo Raspberry Pi (Captura)
- `CamaraStream`: orquesta WifiManager, Camara, enviolmagen y configServicio.
- Transmite imágenes a un servidor externo para su análisis.

### 2. 💻 Servidor Python (Procesamiento)
- `MainController`: inicia y coordina APIServer, FrameProcessor y demás módulos.
- Recibe, procesa e interpreta los fotogramas con YOLO, dibujando los resultados.

Ambos componentes están modelados en UML y siguen principios de diseño orientado a objetos.

---

## 📂 Estructura del Proyecto

BowserSecurity/`\`
├── app/`\`
│   ├── bowSec.py            # Interfaz gráfica y lógica principal`\`
│   ├── models/              # Modelo de detección YOLO`\`
│   ├── capturas/            # Capturas de imágenes realizadas`\`
├── server/`\`
│   ├── main_controller.py   # Procesamiento del lado servidor`\`
├── .env                     # Variables de entorno (claves y credenciales)`\`
├── .gitignore`\`
├── requirements.txt`\`
└── README.md

---

## 🧪 Requisitos del Sistema

### 🔧 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/fernandobeyond/BowserSecurity.git
cd BowserSecurity
```

2.	Instala dependencias:
```
pip install -r requirements.txt
```

3.	Crear el archivo .env con tus credenciales:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
EMAIL_SENDER=tuemail@gmail.com
EMAIL_PASSWORD=app-password-o-contraseña
```

4.	Asegúrate de tener el modelo YOLOv8 (yolov8n.pt) en la carpeta correspondiente.

🚀 Uso del Sistema
1.	Ejecuta la aplicación:
```
python app/bowSec.py
```
2.	Inicia sesión con:
    -	Usuario: Bowser
	-	Contraseña: 12345678

3.	Activa la cámara, captura imágenes, ejecuta análisis y envía alertas por SMS o email.

---

🔐 Seguridad y Buenas Prácticas
-	Las claves y credenciales están protegidas en .env, que está en .gitignore.
-	Se implementa un sistema de logs de autenticación (auth.log).
-	El sistema está preparado para su escalamiento modular.

---

👨‍💻 Contribuciones

Este proyecto se desarrolló como parte del curso Programación Orientada a Objetos (FIEE - UNI).
No se aceptan pull requests públicos, pero puedes hacer forks para uso académico o personal.

---

📜 Licencia

Este repositorio es de uso académico, sin fines comerciales.
© 2025 – Universidad Nacional de Ingeniería, Lima – Perú.