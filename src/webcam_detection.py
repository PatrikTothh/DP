import cv2
from pathlib import Path
from ultralytics import YOLO

# Cesta k hlavnemu priecinku projektu
BASE_DIR = Path(__file__).resolve().parent.parent

# Cesta k natrenovanemu YOLO modelu
MODEL_PATH = BASE_DIR / "models" / "traffic_signs_v1.pt"

# Nacitanie modelu
model = YOLO(str(MODEL_PATH))

# Otvorenie kamery notebooku
cap = cv2.VideoCapture(0)

# Kontrola kamery
if not cap.isOpened():
    raise RuntimeError("Nepodarilo sa otvorit kameru!")

try:
    while True:

        # Nacitanie snimky z kamery
        ret, frame = cap.read()

        if not ret:
            print("Nepodarilo sa nacitat snimku.")
            break

        # Detekcia objektov pomocou YOLO
        results = model.predict(
            source=frame,
            conf=0.35,
            imgsz=512,
            device=0,
            verbose=False
        )

        # Vykreslenie detegovanych objektov
        annotated_frame = results[0].plot()

        # Zobrazenie vysledku
        cv2.imshow("YOLO - Detekcia dopravnych znaciek", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()

    cv2.destroyAllWindows()