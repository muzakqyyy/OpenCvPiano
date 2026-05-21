# hand_detector.py

from dataclasses import dataclass
from math import hypot

import cv2
import mediapipe as mp


@dataclass
class HandInfo:
    handedness: str
    finger_states: dict
    gesture: str | None
    landmarks: list
    bbox: tuple
    center: tuple
    palm_size: float


class HandDetector:

    def __init__(
        self,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
        model_complexity=0,
        mirror_view=True
    ):

        self.mirror_view = mirror_view

        self.mp_hands = mp.solutions.hands

        self.mp_draw = mp.solutions.drawing_utils

        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def close(self):
        self.hands.close()

    def analyze(self, frame):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.hands.process(rgb)

        hand_infos = []

        if not results.multi_hand_landmarks:
            return hand_infos, results

        frame_h, frame_w = frame.shape[:2]

        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):

            handedness = "Unknown"

            if results.multi_handedness:

                handedness = (
                    results.multi_handedness[idx]
                    .classification[0]
                    .label
                )

            if self.mirror_view:

                if handedness == "Left":
                    handedness = "Right"

                elif handedness == "Right":
                    handedness = "Left"

            landmarks_px = []

            xs = []
            ys = []

            for lm in hand_landmarks.landmark:

                x = int(lm.x * frame_w)
                y = int(lm.y * frame_h)

                landmarks_px.append((x, y))

                xs.append(x)
                ys.append(y)

            xmin = min(xs)
            xmax = max(xs)

            ymin = min(ys)
            ymax = max(ys)

            bbox = (xmin, ymin, xmax, ymax)

            center = (
                sum(xs) // len(xs),
                sum(ys) // len(ys)
            )

            palm_size = hypot(
                landmarks_px[0][0] - landmarks_px[9][0],
                landmarks_px[0][1] - landmarks_px[9][1]
            )

            finger_states = self.get_finger_states(
                hand_landmarks.landmark,
                handedness
            )

            gesture = self.get_gesture(
                finger_states
            )

            hand_infos.append(
                HandInfo(
                    handedness=handedness,
                    finger_states=finger_states,
                    gesture=gesture,
                    landmarks=landmarks_px,
                    bbox=bbox,
                    center=center,
                    palm_size=palm_size
                )
            )

        return hand_infos, results

    def draw_landmarks(self, frame, results):

        if not results.multi_hand_landmarks:
            return

        for hand_landmarks in results.multi_hand_landmarks:

            self.mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style()
            )

    def get_finger_states(
        self,
        landmarks,
        handedness
    ):

        fingers = {}

        # =====================================================
        # THUMB
        # =====================================================

        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]

        if handedness == "Right":
            fingers["thumb"] = thumb_tip.x < thumb_ip.x
        else:
            fingers["thumb"] = thumb_tip.x > thumb_ip.x

        # =====================================================
        # OTHER FINGERS
        # =====================================================

        finger_tips = {
            "index": 8,
            "middle": 12,
            "ring": 16,
            "pinky": 20
        }

        finger_pips = {
            "index": 6,
            "middle": 10,
            "ring": 14,
            "pinky": 18
        }

        for finger in finger_tips:

            tip = landmarks[finger_tips[finger]]

            pip = landmarks[finger_pips[finger]]

            fingers[finger] = tip.y < pip.y

        return fingers

    def get_gesture(self, s):

        t = s["thumb"]
        i = s["index"]
        m = s["middle"]
        r = s["ring"]
        p = s["pinky"]

        # ============================================
        # NETRAL
        # ============================================

        # semua terbuka
        if t and i and m and r and p:
            return None

        # semua tertutup
        if not t and not i and not m and not r and not p:
            return None

        # ============================================
        # NOTES
        # ============================================

        # Do
        if not t and i and m and r and p:
            return "thumb_closed"

        # Re
        if t and not i and m and r and p:
            return "index_closed"

        # Mi
        if t and i and not m and r and p:
            return "middle_closed"

        # Fa
        if t and i and m and not r and p:
            return "ring_closed"

        # So
        if t and i and m and r and not p:
            return "pinky_closed"

        # La
        if t and not i and not m and r and p:
            return "index_middle_closed"

        # Si
        if not t and i and m and r and not p:
            return "thumb_pinky_closed"

        return None

    def draw_overlay(
        self,
        frame,
        hand_info,
        stable_gesture=None
    ):

        x1, y1, x2, y2 = hand_info.bbox

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        label = hand_info.handedness

        if stable_gesture:
            label += f" | {stable_gesture}"

        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        yy = y1 + 20

        for finger, state in hand_info.finger_states.items():

            text = "OPEN" if state else "CLOSED"

            color = (
                (0, 255, 0)
                if state
                else
                (0, 0, 255)
            )

            cv2.putText(
                frame,
                f"{finger}: {text}",
                (x1, yy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

            yy += 20