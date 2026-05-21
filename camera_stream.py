# camera_stream.py
# Webcam reader dalam thread terpisah agar main loop tidak blocking.

from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

import cv2


class CameraStream:
    def __init__(
        self,
        source=0,
        width: int = 640,
        height: int = 480,
        reconnect_delay_sec: float = 1.0,
        max_read_fails: int = 30,
    ):
        self.source = source
        self.width = width
        self.height = height
        self.reconnect_delay_sec = reconnect_delay_sec
        self.max_read_fails = max_read_fails

        self._running = False
        self._connected = False
        self._frame = None
        self._lock = threading.Lock()
        self._read_fail_count = 0
        self._cap = None

    def start(self) -> "CameraStream":
        self._running = True
        self._open()
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _open(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass

        cap = cv2.VideoCapture(self.source)

        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._cap = cap
        self._connected = cap.isOpened()

    def _reconnect(self) -> None:
        self._connected = False
        time.sleep(self.reconnect_delay_sec)
        self._open()

    def _update(self) -> None:
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                self._reconnect()
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                self._read_fail_count += 1
                self._connected = False
                if self._read_fail_count >= self.max_read_fails:
                    self._read_fail_count = 0
                    self._reconnect()
                else:
                    time.sleep(0.01)
                continue

            with self._lock:
                self._frame = frame.copy()

            self._connected = True
            self._read_fail_count = 0

    def read(self) -> Tuple[bool, Optional[object]]:
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    def is_connected(self) -> bool:
        return self._connected

    def stop(self) -> None:
        self._running = False
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass

    def join(self, timeout: float = 1.0) -> None:
        if hasattr(self, "_thread"):
            self._thread.join(timeout=timeout)