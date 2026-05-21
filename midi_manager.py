# midi_manager.py
# Kirim note MIDI ke port output / virtual MIDI device.

from __future__ import annotations

import threading
from typing import Optional

import mido

from config import MIDI_CHANNEL, MIDI_NOTE_DURATION_SEC


class MidiManager:
    def __init__(self, output_name: Optional[str] = None):
        self.output = None
        self.enabled = False
        self.channel = MIDI_CHANNEL

        try:
            if output_name:
                self.output = mido.open_output(output_name)
            else:
                ports = mido.get_output_names()
                if ports:
                    self.output = mido.open_output(ports[0])
                else:
                    self.output = None

            if self.output is not None:
                self.enabled = True
                print(f"[INFO] MIDI ready: {self.output.name}")
            else:
                print("[WARNING] Tidak ada MIDI output tersedia.")
        except Exception as e:
            self.enabled = False
            print(f"[WARNING] MIDI nonaktif: {e}")

    def play_note(self, note: int, velocity: int = 90, duration: float = MIDI_NOTE_DURATION_SEC) -> None:
        if not self.enabled or self.output is None:
            return

        note = max(0, min(127, int(note)))
        velocity = max(1, min(127, int(velocity)))

        def _send():
            try:
                self.output.send(mido.Message("note_on", note=note, velocity=velocity, channel=self.channel))
                threading.Timer(duration, self.note_off, args=(note,)).start()
            except Exception as e:
                print(f"[WARNING] MIDI play gagal: {e}")

        threading.Thread(target=_send, daemon=True).start()

    def note_off(self, note: int) -> None:
        if not self.enabled or self.output is None:
            return
        try:
            self.output.send(mido.Message("note_off", note=note, velocity=0, channel=self.channel))
        except Exception:
            pass

    def close(self) -> None:
        if self.output is not None:
            try:
                self.output.close()
            except Exception:
                pass