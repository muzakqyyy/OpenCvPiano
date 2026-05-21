# sound_manager.py

import os
import time
import pygame


class SoundManager:
    """
    Advanced realtime sound manager
    untuk gesture piano.
    """

    def __init__(
        self,
        sound_dir,
        gesture_sound_map,
        cooldown=0.5,
        cooldown_default=None,
        per_gesture_cooldown=None,
        base_volume=1.0,
        **kwargs
    ):
        """
        Parameters
        ----------
        sound_dir : str
            Folder audio.

        gesture_sound_map : dict
            Gesture -> filename mapping.

        cooldown : float
            Cooldown default.

        cooldown_default : float
            Backward compatibility.

        per_gesture_cooldown : dict
            Cooldown khusus per gesture.

        base_volume : float
            Volume global.
        """

        # Backward compatibility
        if cooldown_default is not None:
            cooldown = cooldown_default

        self.sound_dir = sound_dir

        self.gesture_sound_map = gesture_sound_map

        self.default_cooldown = cooldown

        self.per_gesture_cooldown = (
            per_gesture_cooldown or {}
        )

        self.base_volume = max(
            0.0,
            min(1.0, base_volume)
        )

        # Cache timestamp
        self.last_played = {}

        # Cache audio
        self.sounds = {}

        # Init mixer
        pygame.mixer.init()

        # Load audio
        self.load_sounds()

    def load_sounds(self):
        """
        Load seluruh sound.
        """

        if not os.path.exists(self.sound_dir):
            print(f"[WARNING] Folder sounds tidak ada: {self.sound_dir}")
            return

        for gesture, filename in self.gesture_sound_map.items():

            path = os.path.join(
                self.sound_dir,
                filename
            )

            if not os.path.exists(path):
                print(f"[WARNING] File tidak ditemukan: {path}")
                continue

            try:
                sound = pygame.mixer.Sound(path)

                sound.set_volume(self.base_volume)

                self.sounds[gesture] = sound

                print(f"[INFO] Loaded: {filename}")

            except Exception as e:
                print(f"[ERROR] Gagal load {filename}: {e}")

    def get_cooldown(self, gesture):
        """
        Ambil cooldown gesture.
        """

        return self.per_gesture_cooldown.get(
            gesture,
            self.default_cooldown
        )

    def can_play(self, gesture):
        """
        Cek debounce audio.
        """

        current_time = time.time()

        last_time = self.last_played.get(
            gesture,
            0
        )

        cooldown = self.get_cooldown(gesture)

        return (current_time - last_time) >= cooldown

    def play(self, gesture):
        """
        Mainkan audio gesture.
        """

        if gesture is None:
            return

        if gesture not in self.sounds:
            return

        if not self.can_play(gesture):
            return

        try:
            self.sounds[gesture].play()

            self.last_played[gesture] = time.time()

        except Exception as e:
            print(f"[ERROR] Play error: {e}")

    def stop(self, gesture):
        """
        Stop sound tertentu.
        """

        if gesture in self.sounds:
            self.sounds[gesture].stop()

    def stop_all(self):
        """
        Stop semua audio.
        """

        pygame.mixer.stop()

    def set_volume(self, volume):
        """
        Set volume global.
        """

        volume = max(
            0.0,
            min(1.0, volume)
        )

        self.base_volume = volume

        for sound in self.sounds.values():
            sound.set_volume(volume)

    def reload(self):
        """
        Reload seluruh sound.
        """

        self.sounds.clear()

        self.load_sounds()