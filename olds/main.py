import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # Usa modelo personalizado si lo tienes
AGGRESSIVE_CLASSES = ['knife', 'gun']
url = 'https://raspberrybowser.ngrok.app/video'

cap = cv2.VideoCapture(url)

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo recibir el frame")
        break

    results = model(frame)[0]

    people = []
    weapons = []

    for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
        x1, y1, x2, y2 = map(int, box)
        label = model.names[int(cls)]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if label == 'person':
            people.append({'box': (x1, y1, x2, y2), 'center': (cx, cy)})
        elif label in AGGRESSIVE_CLASSES:
            weapons.append({'box': (x1, y1, x2, y2), 'center': (cx, cy), 'label': label})

    # Asignar persona agresiva (la más cercana a un arma)
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
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(frame, weapon['label'].upper(), (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Dibujar personas con etiquetas según cercanía
    for i, person in enumerate(people):
        x1, y1, x2, y2 = person['box']
        if i in aggressive_indices:
            text = "Persona Agresiva"
            color = (0, 0, 255)
        elif weapons:  # hay armas y no es el más cercano
            text = "Víctima"
            color = (0, 255, 255)
        else:
            text = "Persona"
            color = (0, 255, 0)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, text, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Raspberry YOLO Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()