import math
import random
import os
import wave
import struct
import pathlib
import tempfile
import subprocess
import shutil
from typing import List, Dict, Tuple, Optional

from src.utils.paths import get_subprocess_flags
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AdaptiveOLSA:
    """
    Klinischer adaptiver Sprachaudiometrie-Algorithmus nach dem Oldenburger Satztest (OLSA)
    basierend auf dem Standard-Treppenverfahren von Brand & Kollmeier (2002).
    
    Ermittelt die 50% Sprachverstehensschwelle im Störgeräusch (SRT in dB SNR).
    """

    # 5-Wort-Matrix des standardisierten deutschen OLSA-Satztests (10 x 5 Wörter = 100.000 Sätze)
    NAMES = ["Peter", "Michael", "Tanja", "Britta", "Wolfgang", "Kerstin", "Stefan", "Doris", "Ulrich", "Nina"]
    VERBS = ["kauft", "sieht", "gibt", "nimmt", "malt", "bringt", "findet", "zählt", "wählt", "braucht"]
    NUMBERS = ["zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "elf", "zwölf"]
    ADJECTIVES = ["rote", "grüne", "große", "kleine", "nasse", "weiße", "schwere", "gelbe", "alte", "saubere"]
    NOUNS = ["Tassen", "Autos", "Bilder", "Messer", "Schuhe", "Blumen", "Ringe", "Steine", "Kisten", "Sessel"]

    def __init__(self, initial_snr_db: float = 0.0, speech_level_db: float = 65.0, 
                 noise_type: str = "olnoise", total_sentences: int = 20):
        self.speech_level_db = speech_level_db
        self.noise_type = noise_type
        self.total_sentences = total_sentences

        # Laufzeit-Zustand
        self.current_sentence_index = 0
        self.current_snr_db = initial_snr_db
        self.current_target_words: List[str] = []
        self.history: List[Dict] = []
        self.reversals: List[float] = []
        self._last_direction: Optional[int] = None  # +1 (schwieriger), -1 (leichter)

        # Brand & Kollmeier Parameter
        self.target_discrimination = 0.50  # 50% SRT
        self.slope_s = 0.15  # Typische Steilheit der OLSA-Diskriminationskurve (15% pro dB)
        self.c_base = 1.5   # Basiskonstante für adaptive Schrittweiten-Dämpfung

    @classmethod
    def generate_sentence(cls) -> List[str]:
        """Erzeugt einen validen OLSA-Matrixsatz (5 Wörter)."""
        return [
            random.choice(cls.NAMES),
            random.choice(cls.VERBS),
            random.choice(cls.NUMBERS),
            random.choice(cls.ADJECTIVES),
            random.choice(cls.NOUNS)
        ]

    def start_new_test(self, start_snr_db: float = 0.0) -> Dict:
        """Startet eine neue adaptive OLSA-Testreihe."""
        self.current_sentence_index = 0
        self.current_snr_db = start_snr_db
        self.history = []
        self.reversals = []
        self._last_direction = None

        self.current_target_words = self.generate_sentence()
        return {
            "sentence_index": 1,
            "total_sentences": self.total_sentences,
            "current_snr_db": round(self.current_snr_db, 1),
            "target_sentence": " ".join(self.current_target_words),
            "target_words": self.current_target_words,
            "matrix": {
                "names": self.NAMES,
                "verbs": self.VERBS,
                "numbers": self.NUMBERS,
                "adjectives": self.ADJECTIVES,
                "nouns": self.NOUNS
            }
        }

    def process_response(self, selected_words: List[str]) -> Dict:
        """
        Verarbeitet die Patientenauswahl (0..5 Wörter) und berechnet adaptiv den nächsten SNR-Pegel
        nach Brand & Kollmeier (2002).
        """
        if not self.current_target_words:
            self.current_target_words = self.generate_sentence()

        # Ermittle übereinstimmende Wörter
        correct_count = 0
        matched_flags = []
        for i in range(min(5, len(self.current_target_words))):
            target_w = self.current_target_words[i].lower().strip()
            user_w = selected_words[i].lower().strip() if i < len(selected_words) else ""
            is_match = (target_w == user_w)
            if is_match:
                correct_count += 1
            matched_flags.append(is_match)

        fraction_correct = correct_count / 5.0
        applied_snr = self.current_snr_db
        self.current_sentence_index += 1

        # Schrittweiten-Berechnung nach Brand & Kollmeier
        # Variable Schrittweite: größere Schritte zu Beginn, feinere Schritte am Ende
        k_damp = max(0.5, 1.0 - (self.current_sentence_index / (self.total_sentences * 1.5)))
        step_factor = (self.c_base * k_damp) / self.slope_s

        # delta_L: Wenn fraction > 0.50 -> delta_L negativ (SNR wird gesenkt, Test wird schwieriger)
        delta_l = -1.0 * step_factor * (fraction_correct - self.target_discrimination)

        # Begrenze maximale Einzelschrittweite (max. 6 dB Sprung)
        delta_l = max(-6.0, min(6.0, delta_l))

        # Richtungsumkehr (Reversal) protokollieren
        direction = 1 if delta_l < 0 else (-1 if delta_l > 0 else 0)
        if direction != 0:
            if self._last_direction is not None and direction != self._last_direction:
                self.reversals.append(applied_snr)
            self._last_direction = direction

        # Protokolliere Satzdurchlauf
        step_record = {
            "sentence_num": self.current_sentence_index,
            "target": " ".join(self.current_target_words),
            "selected": " ".join(selected_words),
            "correct_words": correct_count,
            "score_pct": round(fraction_correct * 100.0, 1),
            "snr_db": round(applied_snr, 1),
            "matched_flags": matched_flags
        }
        self.history.append(step_record)

        # Nächsten SNR-Pegel setzen (auf 0.5 dB gerastert)
        next_snr = round((applied_snr + delta_l) * 2) / 2.0
        # Physiologische Begrenzung (-20 dB bis +20 dB SNR)
        next_snr = max(-20.0, min(20.0, next_snr))
        self.current_snr_db = next_snr

        # Prüfe, ob Test abgeschlossen ist
        is_finished = (self.current_sentence_index >= self.total_sentences)
        result_data = {
            "finished": is_finished,
            "step_record": step_record,
            "history": self.history,
            "reversals": self.reversals
        }

        if is_finished:
            srt_calc = self.calculate_final_srt()
            result_data["srt_db"] = srt_calc["srt_db"]
            result_data["std_dev"] = srt_calc["std_dev"]
            result_data["mean_snr_last_half"] = srt_calc["mean_snr_last_half"]
        else:
            self.current_target_words = self.generate_sentence()
            result_data["next_sentence_index"] = self.current_sentence_index + 1
            result_data["next_snr_db"] = self.current_snr_db
            result_data["next_target_sentence"] = " ".join(self.current_target_words)
            result_data["next_target_words"] = self.current_target_words

        return result_data

    def calculate_final_srt(self) -> Dict:
        """
        Berechnet den finalen SRT-Wert (Speech Reception Threshold in dB SNR).
        Standard: Mittelwert der letzten 50% der dargebotenen Sätze bzw. Mittelwert der Reversals.
        """
        if not self.history:
            return {"srt_db": 0.0, "std_dev": 0.0, "mean_snr_last_half": 0.0}

        # Nimm die 2. Hälfte der Testläufe (Konvergenzbereich)
        half_idx = len(self.history) // 2
        converged_snrs = [h["snr_db"] for h in self.history[half_idx:]]

        if self.reversals and len(self.reversals) >= 2:
            srt_val = sum(self.reversals[-4:]) / len(self.reversals[-4:])
        elif converged_snrs:
            srt_val = sum(converged_snrs) / len(converged_snrs)
        else:
            srt_val = self.current_snr_db

        # Standardabweichung berechnen
        if len(converged_snrs) > 1:
            mean = sum(converged_snrs) / len(converged_snrs)
            variance = sum((x - mean) ** 2 for x in converged_snrs) / (len(converged_snrs) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        return {
            "srt_db": round(srt_val, 2),
            "std_dev": round(std_dev, 2),
            "mean_snr_last_half": round(sum(converged_snrs) / max(1, len(converged_snrs)), 2)
        }

    @staticmethod
    def _find_ffmpeg() -> str:
        cmd = shutil.which("ffmpeg")
        if cmd:
            return cmd
        for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", "ffmpeg.exe"]:
            if os.path.exists(p):
                return p
        return "ffmpeg"

    @classmethod
    def mix_speech_with_noise(cls, speech_audio_path: str, output_wav_path: str, 
                              snr_db: float, noise_type: str = "olnoise") -> bool:
        """
        Mischt eine Sprach-Audiodatei (MP3 oder WAV) mit definiertem Rauschen bei exaktem Signal-Rausch-Abstand (SNR in dB).
        """
        temp_wav = None
        try:
            # Stelle sicher, dass die Sprache als 16-bit PCM WAV (1 Kanal, 22050 Hz) vorliegt
            ffmpeg_bin = cls._find_ffmpeg()
            os.makedirs(os.path.dirname(output_wav_path) or ".", exist_ok=True)
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name

            cmd_convert = [
                ffmpeg_bin, "-y", "-i", speech_audio_path,
                "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", temp_wav
            ]
            res = subprocess.run(cmd_convert, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
            if res.returncode != 0 or not os.path.exists(temp_wav):
                logger.error(f"[AdaptiveOLSA] Konvertierung fehlgeschlagen: {speech_audio_path}")
                return False

            with wave.open(temp_wav, "rb") as sp_wf:
                n_channels = sp_wf.getnchannels()
                sampwidth = sp_wf.getsampwidth()
                framerate = sp_wf.getframerate()
                n_frames = sp_wf.getnframes()
                raw_speech = sp_wf.readframes(n_frames)

            total_samples = n_frames * n_channels
            speech_samples = list(struct.unpack(f"<{total_samples}h", raw_speech))

            # Berechne Sprach-RMS (Effektivwert)
            sum_sq = sum(s * s for s in speech_samples)
            speech_rms = math.sqrt(sum_sq / max(1, total_samples))
            if speech_rms < 1e-4:
                speech_rms = 1000.0

            # Berechne gewünschten Rausch-RMS aus SNR = 20 * log10(speech_rms / noise_rms)
            noise_rms = speech_rms / (10.0 ** (snr_db / 20.0))

            # Rausch-Generator
            mixed_samples = []
            random.seed(42)  # Reproduzierbares Rauschmuster

            filter_state = 0.0
            alpha = 0.85 if noise_type == "olnoise" else (0.95 if noise_type == "traffic" else 0.0)

            for s in speech_samples:
                white_n = (random.random() * 2.0 - 1.0)
                filter_state = (alpha * filter_state) + ((1.0 - alpha) * white_n)
                shaped_n = filter_state if noise_type != "white" else white_n

                noise_sample = shaped_n * noise_rms * 1.732
                val = int(s + noise_sample)
                val = max(-32767, min(32767, val))
                mixed_samples.append(val)

            packed_out = struct.pack(f"<{len(mixed_samples)}h", *mixed_samples)
            with wave.open(output_wav_path, "wb") as out_wf:
                out_wf.setnchannels(n_channels)
                out_wf.setsampwidth(sampwidth)
                out_wf.setframerate(framerate)
                out_wf.writeframes(packed_out)

            return True
        except Exception as e:
            logger.error(f"[AdaptiveOLSA] Fehler beim Audiomischen: {e}")
            return False
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
