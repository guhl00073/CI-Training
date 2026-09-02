import math
import random
import wave
import struct
import pathlib
import os
import subprocess
import shutil
import tempfile
from typing import List, Tuple, Dict, Optional

from src.utils.paths import get_subprocess_flags
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CIVocoder:
    """
    Akustischer Cochlea-Implantat (CI) Vocoder Simulator.
    
    Zerlegt Audiosignale in N frequenzselektive Bandpasskanäle (basierend auf der tonotopen
    Greenwood-Frequenzverteilung der menschlichen Cochlea) und resynthetisiert das Signal
    über Einhüllenden-Modulation (Noise- oder Sine-Carrier).
    
    Unterstützte Profile:
    - 22 Kanäle: Cochlear Nucleus
    - 16 Kanäle: Advanced Bionics HiRes
    - 12 Kanäle: MED-EL Synchrony
    - 4–8 Kanäle: Didaktische & stark verarmte Hörsimulation
    """

    PROFILES = {
        "cochlear_22": {"name": "Cochlear Nucleus (22 Kanäle)", "channels": 22, "carrier": "sine"},
        "ab_16": {"name": "Advanced Bionics (16 Kanäle)", "channels": 16, "carrier": "sine"},
        "medel_12": {"name": "MED-EL Synchrony (12 Kanäle)", "channels": 12, "carrier": "sine"},
        "training_8": {"name": "Hörtraining Fokus (8 Kanäle)", "channels": 8, "carrier": "sine"},
        "extreme_4": {"name": "Extrem verarmt (4 Kanäle)", "channels": 4, "carrier": "sine"},
    }

    def __init__(self, low_freq: float = 150.0, high_freq: float = 8000.0):
        self.low_freq = low_freq
        self.high_freq = high_freq

    @staticmethod
    def _find_ffmpeg() -> str:
        cmd = shutil.which("ffmpeg")
        if cmd:
            return cmd
        for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", "ffmpeg.exe"]:
            if os.path.exists(p):
                return p
        return "ffmpeg"

    def get_greenwood_bands(self, num_channels: int) -> List[Tuple[float, float, float]]:
        """
        Berechnet die Eck- und Mittenfrequenzen für N Kanäle nach der Greenwood-Funktion:
        f(x) = A * (10^(a * x) - k) mit humanen Cochlea-Parametern (Greenwood, 1990).
        """
        # Greenwood Parameter für den Menschen (0.0 = Apex, 1.0 = Base)
        A = 165.4
        a = 2.1
        k = 0.88

        # Berechne x-Positionen entlang der Basilarmembran [0.0 = Apex/Tiefen, 1.0 = Basis/Höhen]
        # Invertiere Greenwood: x = (1/a) * log10(f / A + k)
        x_min = (1.0 / a) * math.log10((self.low_freq / A) + k)
        x_max = (1.0 / a) * math.log10((self.high_freq / A) + k)

        dx = (x_max - x_min) / num_channels
        bands = []

        for i in range(num_channels):
            x_low = x_min + (i * dx)
            x_high = x_min + ((i + 1) * dx)
            x_center = (x_low + x_high) / 2.0

            f_low = A * ((10.0 ** (a * x_low)) - k)
            f_high = A * ((10.0 ** (a * x_high)) - k)
            f_center = A * ((10.0 ** (a * x_center)) - k)

            bands.append((max(20.0, f_low), min(20000.0, f_high), f_center))

        return bands

    def process_wav(self, input_audio_path: str, output_wav_path: str, 
                    num_channels: int = 16, carrier_type: str = "noise") -> bool:
        """
        Wandelt eine Audiosprachdatei (MP3 oder WAV) in eine CI-Vocoder-Simulation um.
        """
        temp_wav = None
        try:
            # Konvertiere in 16-bit PCM WAV (1 Kanal, 22050 Hz)
            ffmpeg_bin = self._find_ffmpeg()
            os.makedirs(os.path.dirname(output_wav_path) or ".", exist_ok=True)
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

            cmd_convert = [
                ffmpeg_bin, "-y", "-i", input_audio_path,
                "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", temp_wav
            ]
            res = subprocess.run(cmd_convert, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
            if res.returncode != 0 or not os.path.exists(temp_wav):
                return False

            with wave.open(temp_wav, "rb") as in_wf:
                n_channels = in_wf.getnchannels()
                sampwidth = in_wf.getsampwidth()
                framerate = in_wf.getframerate()
                n_frames = in_wf.getnframes()
                raw_bytes = in_wf.readframes(n_frames)

            total_samples = n_frames * n_channels
            samples = list(struct.unpack(f"<{total_samples}h", raw_bytes))

            # Normalisiere Eingangssignal auf [-1.0, 1.0]
            float_samples = [s / 32768.0 for s in samples]

            # Frequenzbänder berechnen
            bands = self.get_greenwood_bands(num_channels)

            envelope_cutoff = 400.0
            dt = 1.0 / framerate
            rc = 1.0 / (2.0 * math.pi * envelope_cutoff)
            lp_alpha = dt / (rc + dt)

            synth_signal = [0.0] * len(float_samples)
            random.seed(1337)

            for band_idx, (f_low, f_high, f_center) in enumerate(bands):
                bw = f_high - f_low
                q = f_center / max(10.0, bw)
                w0 = 2.0 * math.pi * f_center / framerate
                alpha_bp = math.sin(w0) / (2.0 * max(0.1, q))

                b0 = alpha_bp
                b1 = 0.0
                b2 = -alpha_bp
                a0 = 1.0 + alpha_bp
                a1 = -2.0 * math.cos(w0)
                a2 = 1.0 - alpha_bp

                b0 /= a0
                b1 /= a0
                b2 /= a0
                a1 /= a0
                a2 /= a0

                x1 = x2 = y1 = y2 = 0.0
                env_state = 0.0
                carrier_phase = 0.0
                phase_inc = 2.0 * math.pi * f_center / framerate

                for idx, x in enumerate(float_samples):
                    # Bandpass-Filterung
                    y = (b0 * x) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)
                    x2, x1 = x1, x
                    y2, y1 = y1, y

                    # Vollweggleichrichtung & Einhüllenden-Tiefpass (Hilbert-Approximation)
                    rect = abs(y)
                    env_state = (1.0 - lp_alpha) * env_state + (lp_alpha * rect)

                    carrier = math.sin(carrier_phase)
                    carrier_phase += phase_inc
                    if carrier_phase > 2.0 * math.pi:
                        carrier_phase -= 2.0 * math.pi

                    synth_signal[idx] += env_state * carrier

            # Normalisieren und Skalieren
            max_amp = max(max(abs(s) for s in synth_signal), 1e-4)
            scale = 0.85 / max_amp

            out_int16 = []
            for s in synth_signal:
                val = int(s * scale * 32767.0)
                val = max(-32767, min(32767, val))
                out_int16.append(val)

            packed = struct.pack(f"<{len(out_int16)}h", *out_int16)
            with wave.open(output_wav_path, "wb") as out_wf:
                out_wf.setnchannels(n_channels)
                out_wf.setsampwidth(sampwidth)
                out_wf.setframerate(framerate)
                out_wf.writeframes(packed)

            return True
        except Exception as e:
            logger.error(f"[CIVocoder] Fehler bei CI-Simulation: {e}")
            return False
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
