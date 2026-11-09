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

from changedetection import ChangeDetection, StablePresence


class ChangeDetectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.post = patch("changedetection.requests.post").start()
        patch("builtins.print").start()
        self.addCleanup(patch.stopall)
        self.post.return_value.json.return_value = {"token": "test-token"}
        with patch.dict(os.environ, {"YOLO_USERNAME": "test", "YOLO_PASSWORD": "test"}):
            self.names = {0: "person", 1: "bottle"}
            self.detector = ChangeDetection(self.names)
        self.filter = None
        self.post.reset_mock()
        self.post.return_value.json.return_value = {"id": 7}
        self.image = np.zeros((480, 640, 3), dtype=np.uint8)

    def add(self, state):
        if self.filter is not None:
            state = self.filter.update(state)
        return self.detector.add(self.names, state, self.directory.name, self.image)

    def test_empty_and_steady_frames_do_not_duplicate_posts(self):
        self.add([0, 0])
        self.post.assert_not_called()
        self.add([1, 0])
        self.add([1, 0])
        self.post.assert_called_once()

    def test_reappearance_sends_again_and_removal_alone_does_not(self):
        self.filter = StablePresence(2, 2)
        with patch("changedetection.time.monotonic", side_effect=[0.0, 0.1, 2.1, 2.2]):
            self.add([1, 0])
            self.add([0, 0])
            self.add([0, 0])
            self.assertEqual(self.post.call_count, 1)
            self.add([1, 0])
        self.assertEqual(self.post.call_count, 2)

    def test_intermittent_misses_do_not_create_repeated_posts(self):
        self.filter = StablePresence(2, 2)
        with patch("changedetection.time.monotonic") as clock:
            for i in range(100):
                clock.return_value = i * 0.1
                self.add([1, 0] if i % 10 == 0 else [0, 0])
        self.post.assert_called_once()

    def test_just_under_absence_limit_does_not_rearm(self):
        self.filter = StablePresence(2, 2)
        with patch("changedetection.time.monotonic", side_effect=[0.0, 1.0, 2.99, 3.0]):
            self.add([1, 0])
            self.add([0, 0])
            self.add([0, 0])
            self.add([1, 0])
        self.post.assert_called_once()

    def test_new_class_is_sent_even_while_another_class_is_held(self):
        self.filter = StablePresence(2, 2)
        with patch("changedetection.time.monotonic", side_effect=[0.0, 0.1]):
            self.add([1, 0])
            self.add([0, 1])
        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.post.call_args.kwargs["data"]["title"], "bottle")

    def test_zero_absence_preserves_original_lecture_rule(self):
        self.add([1, 0])
        self.add([0, 0])
        self.add([1, 0])
        self.assertEqual(self.post.call_count, 2)

    def test_invalid_absence_is_rejected_before_login(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                StablePresence(1, value)
        self.post.assert_not_called()

    def test_multiple_new_classes_share_one_image_and_use_token_auth(self):
        self.add([1, 1])
        self.post.assert_called_once()
        self.assertEqual(self.post.call_args.kwargs["headers"]["Authorization"], "Token test-token")
        self.assertEqual(self.post.call_args.kwargs["data"]["title"], "bottle")
        self.assertEqual(self.post.call_args.kwargs["data"]["text"], "person, bottle, ")
        images = list(Path(self.directory.name).rglob("*.jpg"))
        self.assertEqual(len(images), 1)
        self.assertEqual(cv2.imread(str(images[0])).shape[:2], (240, 320))
        self.assertTrue(self.post.call_args.kwargs["files"]["image"].closed)

    def test_existing_class_does_not_hide_a_new_class(self):
        self.add([1, 0])
        self.add([1, 1])
        self.assertEqual(self.post.call_args.kwargs["data"]["title"], "bottle")

    def test_previous_state_is_a_copy_of_the_input(self):
        state = [1, 0]
        self.add(state)
        state[0] = 0
        self.add([1, 0])
        self.post.assert_called_once()

    def test_network_failure_raises_and_keeps_the_saved_image(self):
        self.post.side_effect = requests.ConnectionError("offline")
        with self.assertRaises(requests.ConnectionError):
            self.add([1, 0])
        self.add([1, 0])
        self.post.assert_called_once()
        self.assertEqual(len(list(Path(self.directory.name).rglob("*.jpg"))), 1)

    def test_bad_login_is_not_treated_as_success(self):
        self.post.return_value.raise_for_status.side_effect = requests.HTTPError("401")
        with patch.dict(os.environ, {"YOLO_USERNAME": "test", "YOLO_PASSWORD": "wrong"}):
            with self.assertRaises(requests.HTTPError):
                ChangeDetection({0: "person"})


if __name__ == "__main__":
    unittest.main()
