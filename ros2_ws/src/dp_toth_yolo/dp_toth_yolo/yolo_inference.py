from ultralytics import YOLO


class YoloInference:

    def __init__(self, model_path, confidence, image_size, device):

        # Nacitanie natrenovaneho modelu
        self.model = YOLO(model_path)

        # Parametre detekcie
        self.confidence = confidence
        self.image_size = image_size
        self.device = device

    def predict(self, frame):

        # Vykonanie detekcie
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            imgsz=self.image_size,
            device=self.device,
            verbose=False
        )

        return results[0]