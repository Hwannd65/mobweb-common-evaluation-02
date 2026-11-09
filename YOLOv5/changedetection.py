# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Upload a detection image when a class changes from absent to present (Ch08)."""

import getpass
import logging
import math
import os
import time
from datetime import datetime
from pathlib import Path

import cv2
import requests

LOGGER = logging.getLogger("ultralytics")


class ChangeDetection:
    """Remember class presence per source and send newly appearing classes to Django."""

    def __init__(self, names, host="http://127.0.0.1:8000", absence_seconds=2.0):
        if not math.isfinite(absence_seconds) or absence_seconds < 0:
            raise ValueError("absence_seconds must be a finite, non-negative number")
        self.names = names
        self.host = host.rstrip("/")
        self.absence_seconds = absence_seconds
        self.result_prev = {}
        self.missing_since = {}
        self.session = requests.Session()
        username = os.environ.get("YOLO_USERNAME") or input("Django username: ")
        password = os.environ.get("YOLO_PASSWORD") or getpass.getpass("Django password: ")
        response = self.session.post(
            self.host + "/api-token-auth/",
            data={"username": username, "password": password},
            timeout=(3, 10),
        )
        response.raise_for_status()
        self.session.headers.update({"Authorization": "Token " + response.json()["token"]})
        LOGGER.info("Django login successful: %s", self.host)

    def add(self, detected_current, save_dir, image, source="0"):
        """Confirm sustained absence before treating a later detection as a new arrival."""
        previous = self.result_prev.get(source, [0] * len(self.names))
        missing = self.missing_since.setdefault(source, [None] * len(self.names))
        current = detected_current[:]
        now = time.monotonic()
        for i, detected in enumerate(detected_current):
            if detected:
                missing[i] = None
            elif previous[i]:
                if missing[i] is None:
                    missing[i] = now
                if now - missing[i] < self.absence_seconds:
                    current[i] = 1
        appeared = [self.names[i] for i in range(len(self.names)) if previous[i] == 0 and current[i] == 1]
        self.result_prev[source] = current
        if not appeared:
            return None
        try:
            return self.send(appeared, save_dir, image)
        except (requests.RequestException, OSError, cv2.error) as error:
            # Keep the local image and allow live detection to continue on upload failure.
            LOGGER.warning("Django upload failed (%s). Detection continues; check the server and detected/ images.", error)
            return None

    def send(self, appeared, save_dir, image):
        """Save the annotated frame locally and upload it as a multipart post."""
        now = datetime.now()
        directory = Path(save_dir) / "detected" / now.strftime("%Y/%m/%d")
        directory.mkdir(parents=True, exist_ok=True)
        filename = directory / (now.strftime("%H-%M-%S-%f") + ".jpg")
        resized = cv2.resize(image, (320, 240), interpolation=cv2.INTER_AREA)
        if not cv2.imwrite(str(filename), resized):
            raise OSError(f"Could not save detection image: {filename}")
        text = ", ".join(appeared)
        with filename.open("rb") as image_file:
            response = self.session.post(
                self.host + "/api_root/Post/",
                data={"title": text[:200], "text": "Newly detected: " + text},
                files={"image": (filename.name, image_file, "image/jpeg")},
                timeout=(3, 10),
            )
        response.raise_for_status()
        post = response.json()
        LOGGER.info("Django post created: id=%s, classes=%s, image=%s", post["id"], text, filename)
        return post
