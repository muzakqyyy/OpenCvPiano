# config.py
# Konfigurasi utama project MIDI gesture piano.

# Webcam laptop
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
MIRROR_VIEW = True

# Capture
RECONNECT_DELAY_SEC = 1.0
MAX_READ_FAILS = 30

# MediaPipe
MAX_NUM_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7
MODEL_COMPLEXITY = 0  # 0 lebih ringan, 1 lebih akurat tapi lebih berat

# Smoothing gesture
SMOOTHING_WINDOW = 5
MIN_SAME_GESTURE_FRAMES = 3
NEUTRAL_RESET_FRAMES = 2

# MIDI
MIDI_ENABLED = True
MIDI_OUTPUT_NAME = None  # isi nama port kalau mau pilih device tertentu
MIDI_CHANNEL = 0
MIDI_NOTE_DURATION_SEC = 0.18
MIDI_VELOCITY_BASE = 90
MIDI_VELOCITY_MIN = 40
MIDI_VELOCITY_MAX = 127

# Gesture to MIDI note mapping
# C major scale 1 octave
GESTURE_MIDI_MAP = {
    "thumb_closed": 60,          # Do / C4
    "index_closed": 62,          # Re / D4
    "middle_closed": 64,         # Mi / E4
    "ring_closed": 65,           # Fa / F4
    "pinky_closed": 67,          # So / G4
    "index_middle_closed": 69,   # La / A4
    "all_closed": 71,            # Si / B4
    "thumb_pinky_closed": 72,    # Do tinggi / C5
}

GESTURE_LABELS = {
    "thumb_closed": "Do",
    "index_closed": "Re",
    "middle_closed": "Mi",
    "ring_closed": "Fa",
    "pinky_closed": "So",
    "index_middle_closed": "La",
    "all_closed": "Si",
    "thumb_pinky_closed": "Do tinggi",
}

# Threshold adaptif
BASE_OPEN_THRESHOLD = 0.020
BASE_CLOSED_THRESHOLD = 0.010
PALM_EMA_ALPHA = 0.18

# Motion -> velocity
MOTION_SPEED_REF = 1400.0
MOTION_VELOCITY_BOOST = 45
LEFT_HAND_OPEN_GAIN = 0.04