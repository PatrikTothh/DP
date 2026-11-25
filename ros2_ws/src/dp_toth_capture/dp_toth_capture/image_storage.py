import csv
import re
from datetime import datetime
from pathlib import Path

import cv2


class ImageStorage:

    def __init__(
        self,
        output_dir,
        image_format="jpg",
        jpeg_quality=95,
        session_name="default"
    ):  

        self.image_format = image_format.lower()
        self.jpeg_quality = jpeg_quality

        if self.image_format not in ("jpg", "png"):
            raise ValueError("Podporovane formaty su jpg a png.")

        if not 0 <= self.jpeg_quality <= 100:
            raise ValueError("JPEG kvalita musi byt od 0 do 100.")

        # Hlavny priecinok
        self.output_dir = Path(output_dir).expanduser()

        # Kontrola nazvu priecinka
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", session_name):
            raise ValueError(
                "Nazov priecinka moze obsahovat iba pismena, "
                "cislice, pomlcky a podciarkovniky."
            )

        # Casova znacka zachytavania
        timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S_%f")

        # Vytvorenie priecinka
        self.session_dir = self.output_dir / session_name / timestamp

        self.images_dir = self.session_dir / "images"

        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Pocitadlo obrazkov
        self.counter = 0

        # Subor s metadatami
        self.metadata_path = self.session_dir / "metadata.csv"

        with open(self.metadata_path, "w", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                "filename",
                "timestamp",
                "capture_mode"
            ])

    def save(self, frame, capture_mode="manual"):

        timestamp = datetime.now().astimezone()

        # Jedinecny nazov obrazka
        filename = (
            f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_"
            f"{self.counter:06d}.{self.image_format}"
        )

        file_path = self.images_dir / filename

        # Parametre ukladania
        if self.image_format == "jpg":

            parameters = [
                cv2.IMWRITE_JPEG_QUALITY,
                self.jpeg_quality
            ]

        else:

            parameters = []

        # Ulozenie obrazka
        success = cv2.imwrite(
            str(file_path),
            frame,
            parameters
        )

        if not success:
            raise RuntimeError(f"Nepodarilo sa ulozit: {file_path}")

        # Zapis metadat
        with open(self.metadata_path, "a", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)

            writer.writerow([
                filename,
                timestamp.isoformat(timespec="milliseconds"),
                capture_mode
            ])

        self.counter += 1

        return file_path