# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Ch08 pages 8-10: login, detect class appearances, and upload an image."""

import getpass
import math
import os
import pathlib
import time
from datetime import datetime

import cv2
import requests


class ChangeDetection:
    result_prev = []
    HOST = "http://127.0.0.1:8000"
    username = ""
    password = ""
    token = ""
    title = ""
    text = ""

    def __init__(self, names, host=None):
        if host:
            self.HOST = host.rstrip("/")
        self.result_prev = [0 for i in range(len(names))]
        # Enter real credentials at runtime; never save or print them in source.
        self.username = os.environ.get("YOLO_USERNAME") or input("Django username: ")
        self.password = os.environ.get("YOLO_PASSWORD") or getpass.getpass("Django password: ")
        res = requests.post(
            self.HOST + "/api-token-auth/",
            {"username": self.username, "password": self.password},
            timeout=(3, 10),
        )
        res.raise_for_status()
        self.token = res.json()["token"]

    def add(self, names, detected_current, save_dir, image):
        self.title = ""
        self.text = ""
        change_flag = 0
        i = 0
        while i < len(self.result_prev):
            if self.result_prev[i] == 0 and detected_current[i] == 1:
                change_flag = 1
                self.title = names[i]
                self.text += names[i] + ", "
            i += 1
        self.result_prev = detected_current[:]
        if change_flag == 1:
            self.send(save_dir, image)

    def send(self, save_dir, image):
        now = datetime.now()
        today = now
        save_path = pathlib.Path(save_dir) / "detected" / str(today.year) / str(today.month) / str(today.day)
        pathlib.Path(save_path).mkdir(parents=True, exist_ok=True)
        full_path = save_path / "{0}-{1}-{2}-{3}.jpg".format(
            today.hour, today.minute, today.second, today.microsecond
        )
        dst = cv2.resize(image, dsize=(320, 240), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(full_path), dst)
        # This Django server uses DRF TokenAuthentication rather than JWT.
        headers = {"Authorization": "Token " + self.token, "Accept": "application/json"}
        data = {
            "title": self.title,
            "text": self.text,
            "created_date": now,
            "published_date": now,
        }
        with full_path.open("rb") as image_file:
            file = {"image": image_file}
            res = requests.post(
                self.HOST + "/api_root/Post/", data=data, files=file, headers=headers, timeout=(3, 10)
            )
        res.raise_for_status()
        print(res)
        print(f"Django post created: id={res.json()['id']}, classes={self.text}, image={full_path}")


class StablePresence:
    """Optional convenience feature: hold presence through brief missed detections."""

    def __init__(self, count, absence_seconds):
        if not math.isfinite(absence_seconds) or absence_seconds < 0:
            raise ValueError("absence_seconds must be a finite, non-negative number")
        self.absence_seconds = absence_seconds
        self.previous = [0] * count
        self.missing_since: list[float | None] = [None] * count

    def update(self, detected_current):
        current = detected_current[:]
        now = time.monotonic()
        for i, detected in enumerate(detected_current):
            if detected:
                self.missing_since[i] = None
            elif self.previous[i]:
                missing_since = self.missing_since[i]
                if missing_since is None:
                    missing_since = now
                    self.missing_since[i] = missing_since
                if now - missing_since < self.absence_seconds:
                    current[i] = 1
        self.previous = current
        return current
