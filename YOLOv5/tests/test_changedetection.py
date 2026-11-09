# Ultralytics 🚀 AGPL-3.0 License - https://ultralytics.com/license
"""Focused checks for Ch08 transitions, authentication and image uploads."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import requests

from changedetection import ChangeDetection


class ChangeDetectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.factory = patch("changedetection.requests.Session").start()
        self.addCleanup(patch.stopall)
        self.session = self.factory.return_value
        self.session.headers = {}
        self.session.post.return_value.json.return_value = {"token": "test-token"}
        with patch.dict(os.environ, {"YOLO_USERNAME": "test", "YOLO_PASSWORD": "test"}):
            self.detector = ChangeDetection({0: "person", 1: "bottle"})
        self.session.post.reset_mock()
        self.session.post.return_value.json.return_value = {"id": 7}
        self.image = np.zeros((480, 640, 3), dtype=np.uint8)

    def add(self, state, source="camera"):
        return self.detector.add(state, self.directory.name, self.image, source)

    def test_empty_and_steady_frames_do_not_duplicate_posts(self):
        self.add([0, 0])
        self.session.post.assert_not_called()
        self.assertEqual(self.add([1, 0]), {"id": 7})
        self.add([1, 0])
        self.session.post.assert_called_once()

    def test_reappearance_sends_again_and_removal_alone_does_not(self):
        with patch("changedetection.time.monotonic", side_effect=[0.0, 0.1, 2.1, 2.2]):
            self.add([1, 0])
            self.add([0, 0])
            self.add([0, 0])
            self.assertEqual(self.session.post.call_count, 1)
            self.add([1, 0])
        self.assertEqual(self.session.post.call_count, 2)

    def test_intermittent_misses_do_not_create_repeated_posts(self):
        with patch("changedetection.time.monotonic") as clock:
            for i in range(100):
                clock.return_value = i * 0.1
                self.add([1, 0] if i % 10 == 0 else [0, 0])
        self.session.post.assert_called_once()

    def test_just_under_absence_limit_does_not_rearm(self):
        with patch("changedetection.time.monotonic", side_effect=[0.0, 1.0, 2.99, 3.0]):
            self.add([1, 0])
            self.add([0, 0])
            self.add([0, 0])
            self.add([1, 0])
        self.session.post.assert_called_once()

    def test_new_class_is_sent_even_while_another_class_is_held(self):
        with patch("changedetection.time.monotonic", side_effect=[0.0, 0.1]):
            self.add([1, 0])
            self.add([0, 1])
        self.assertEqual(self.session.post.call_count, 2)
        self.assertEqual(self.session.post.call_args.kwargs["data"]["title"], "bottle")

    def test_zero_absence_preserves_original_lecture_rule(self):
        self.detector.absence_seconds = 0
        self.add([1, 0])
        self.add([0, 0])
        self.add([1, 0])
        self.assertEqual(self.session.post.call_count, 2)

    def test_invalid_absence_is_rejected_before_login(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                ChangeDetection({0: "person"}, absence_seconds=value)

    def test_multiple_new_classes_share_one_image_and_use_token_auth(self):
        self.add([1, 1])
        self.session.post.assert_called_once()
        self.assertEqual(self.session.headers["Authorization"], "Token test-token")
        self.assertEqual(self.session.post.call_args.kwargs["data"]["title"], "person, bottle")
        images = list(Path(self.directory.name).rglob("*.jpg"))
        self.assertEqual(len(images), 1)
        self.assertEqual(cv2.imread(str(images[0])).shape[:2], (240, 320))
        self.assertTrue(self.session.post.call_args.kwargs["files"]["image"][1].closed)

    def test_existing_class_does_not_hide_a_new_class(self):
        self.add([1, 0])
        self.add([1, 1])
        self.assertEqual(self.session.post.call_args.kwargs["data"]["title"], "bottle")

    def test_streams_keep_independent_history(self):
        self.add([1, 0], "camera-1")
        self.add([1, 0], "camera-2")
        self.assertEqual(self.session.post.call_count, 2)

    def test_network_failure_keeps_image_without_flooding_server(self):
        self.session.post.side_effect = requests.ConnectionError("offline")
        with self.assertLogs("ultralytics", level="WARNING"):
            self.assertIsNone(self.add([1, 0]))
        self.add([1, 0])
        self.session.post.assert_called_once()
        self.assertEqual(len(list(Path(self.directory.name).rglob("*.jpg"))), 1)

    def test_bad_login_is_not_treated_as_success(self):
        self.session.post.return_value.raise_for_status.side_effect = requests.HTTPError("401")
        with patch.dict(os.environ, {"YOLO_USERNAME": "test", "YOLO_PASSWORD": "wrong"}):
            with self.assertRaises(requests.HTTPError):
                ChangeDetection({0: "person"})


if __name__ == "__main__":
    unittest.main()
