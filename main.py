# main.py
# Webcam laptop -> MediaPipe -> gesture -> MIDI output.

from __future__ import annotations

import time
from collections import Counter, deque
from math import hypot
from typing import Optional

import cv2

from camera_stream import CameraStream
from config import (
    CAMERA_INDEX,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    GESTURE_LABELS,
    GESTURE_MIDI_MAP,
    LEFT_HAND_OPEN_GAIN,
    MAX_NUM_HANDS,
    MAX_READ_FAILS,
    MIDI_ENABLED,
    MIDI_NOTE_DURATION_SEC,
    MIDI_OUTPUT_NAME,
    MIDI_VELOCITY_BASE,
    MIDI_VELOCITY_MAX,
    MIDI_VELOCITY_MIN,
    MODEL_COMPLEXITY,
    MIRROR_VIEW,
    MIN_DETECTION_CONFIDENCE,
    MIN_SAME_GESTURE_FRAMES,
    MIN_TRACKING_CONFIDENCE,
    MOTION_SPEED_REF,
    MOTION_VELOCITY_BOOST,
    NEUTRAL_RESET_FRAMES,
    RECONNECT_DELAY_SEC,
    SMOOTHING_WINDOW,
)
from hand_detector import HandDetector
from midi_manager import MidiManager

cv2.setUseOptimized(True)


class GestureSmoother:
    def __init__(self, window_size: int = 5, min_same_frames: int = 3):
        self.history = deque(maxlen=window_size)
        self.min_same_frames = min_same_frames

    def update(self, gesture: Optional[str]) -> Optional[str]:
        if gesture is not None:
            self.history.append(gesture)

        if len(self.history) < self.min_same_frames:
            return None

        most_common, count = Counter(self.history).most_common(1)[0]
        if count >= self.min_same_frames:
            return most_common
        return None

    def reset(self) -> None:
        self.history.clear()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def draw_status(frame, fps: float, camera_ok: bool, stable_gesture: Optional[str], note_label: str) -> None:
    cv2.rectangle(frame, (10, 10), (420, 100), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (420, 100), (255, 255, 255), 1)

    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(
        frame,
        f"Camera: {'ON' if camera_ok else 'RECONNECTING'}",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )
    text = note_label if note_label else "Base / Neutral"
    if stable_gesture:
        text = f"{note_label} ({stable_gesture})"
    cv2.putText(frame, f"Note: {text}", (20, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def choose_trigger_hand(hand_infos):
    right_candidate = None
    any_candidate = None

    for idx, hand in enumerate(hand_infos):
        if hand.gesture is None:
            continue
        if hand.handedness == "Right":
            right_candidate = (idx, hand)
            break
        if any_candidate is None:
            any_candidate = (idx, hand)

    return right_candidate or any_candidate


def get_expression_hand(hand_infos, trigger_index: Optional[int]):
    if trigger_index is None:
        return None

    trigger_hand = hand_infos[trigger_index]
    for idx, hand in enumerate(hand_infos):
        if idx != trigger_index and hand.handedness != trigger_hand.handedness:
            return hand
    return None


def motion_speed(prev_center, prev_time, current_center, current_time) -> float:
    if prev_center is None or prev_time is None:
        return 0.0
    dt = max(current_time - prev_time, 1e-6)
    dist = hypot(current_center[0] - prev_center[0], current_center[1] - prev_center[1])
    return dist / dt


def main():
    camera = CameraStream(
        source=CAMERA_INDEX,
        width=FRAME_WIDTH,
        height=FRAME_HEIGHT,
        reconnect_delay_sec=RECONNECT_DELAY_SEC,
        max_read_fails=MAX_READ_FAILS,
    ).start()

    detector = HandDetector(
        max_num_hands=MAX_NUM_HANDS,
        min_detection_confidence=MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
        model_complexity=MODEL_COMPLEXITY,
        mirror_view=MIRROR_VIEW,
    )

    midi = MidiManager(output_name=MIDI_OUTPUT_NAME) if MIDI_ENABLED else None

    cv2.namedWindow("Gesture MIDI Laptop", cv2.WINDOW_NORMAL)

    smoother = GestureSmoother(SMOOTHING_WINDOW, MIN_SAME_GESTURE_FRAMES)
    prev_time = time.time()

    prev_centers = {"Left": None, "Right": None, "Unknown": None}
    prev_center_times = {"Left": None, "Right": None, "Unknown": None}
    speed_ema = {"Left": 0.0, "Right": 0.0, "Unknown": 0.0}

    neutral_frames = 0
    last_triggered_gesture: Optional[str] = None

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue

            if MIRROR_VIEW:
                frame = cv2.flip(frame, 1)

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            hand_infos, results = detector.analyze(frame)
            detector.draw_landmarks(frame, results)

            trigger = choose_trigger_hand(hand_infos)
            stable_gesture = None
            note_label = ""

            if trigger is not None:
                trigger_idx, trigger_hand = trigger
                neutral_frames = 0

                if trigger_hand.gesture is not None:
                    stable_gesture = smoother.update(trigger_hand.gesture)
                else:
                    stable_gesture = smoother.update(None)

                if stable_gesture in GESTURE_LABELS:
                    note_label = GESTURE_LABELS[stable_gesture]

                now = time.time()
                prev_center = prev_centers.get(trigger_hand.handedness)
                prev_center_time = prev_center_times.get(trigger_hand.handedness)
                speed = motion_speed(prev_center, prev_center_time, trigger_hand.center, now)

                prev_centers[trigger_hand.handedness] = trigger_hand.center
                prev_center_times[trigger_hand.handedness] = now

                speed_ema[trigger_hand.handedness] = 0.75 * speed_ema[trigger_hand.handedness] + 0.25 * speed
                motion_factor = clamp(speed_ema[trigger_hand.handedness] / MOTION_SPEED_REF, 0.0, 1.0)

                base_velocity = MIDI_VELOCITY_BASE + int(motion_factor * MOTION_VELOCITY_BOOST)
                base_velocity = int(clamp(base_velocity, MIDI_VELOCITY_MIN, MIDI_VELOCITY_MAX))

                # tangan kedua bisa jadi kontrol ekspresi kecil
                expression_hand = get_expression_hand(hand_infos, trigger_idx)
                expression_gain = 1.0
                if expression_hand is not None:
                    open_count = sum(1 for v in expression_hand.finger_states.values() if v)
                    expression_gain = clamp(0.82 + (open_count * LEFT_HAND_OPEN_GAIN), 0.75, 1.15)

                final_velocity = int(clamp(base_velocity * expression_gain, MIDI_VELOCITY_MIN, MIDI_VELOCITY_MAX))

                if stable_gesture is not None and stable_gesture != last_triggered_gesture:
                    if stable_gesture in GESTURE_MIDI_MAP and midi is not None:
                        note = GESTURE_MIDI_MAP[stable_gesture]
                        midi.play_note(note, velocity=final_velocity)
                        last_triggered_gesture = stable_gesture
                        print(f"[INFO] MIDI note {note} | gesture={stable_gesture} | vel={final_velocity}")

            else:
                neutral_frames += 1
                if neutral_frames >= NEUTRAL_RESET_FRAMES:
                    smoother.reset()
                    last_triggered_gesture = None

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            draw_status(frame, fps, camera.is_connected(), stable_gesture, note_label)

            for idx, hand in enumerate(hand_infos):
                detector.draw_overlay(
                    frame,
                    hand,
                    stable_gesture if trigger is not None and idx == trigger[0] else None,
                )

            cv2.imshow("Gesture MIDI Laptop", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    finally:
        camera.stop()
        camera.join(timeout=1.0)
        detector.close()
        if midi is not None:
            midi.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()