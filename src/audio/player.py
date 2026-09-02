import subprocess
import os
import tempfile
import pathlib
import threading
import sys
import shutil
import atexit
import uuid

from src.utils.paths import get_resource_path, get_subprocess_flags
from src.utils.logger import get_logger

logger = get_logger(__name__)
class AudioPlayer:
    """
    Audio Player Engine tailored for Cochlear Implant (CI) users.
    Supports macOS, Windows, and Linux cross-platform execution.
    Features stereo panning, speech rate, continuous contralateral masking, and Störschall noise.
    """
    def __init__(self, noise_file: str = None):
        self.speech_process = None
        self.noise_process = None
        self.noise_processes = []
        if noise_file is None:
            self.noise_file = str(get_resource_path("data/rauschen.mp3"))
        else:
            self.noise_file = os.path.abspath(noise_file)
        self.ambient_files = {
            "noise":      self.noise_file,
            "restaurant": str(get_resource_path("data/ambient_restaurant.wav")),
            "cafe":       str(get_resource_path("data/ambient_restaurant.wav")),
            "traffic":    str(get_resource_path("data/ambient_traffic.wav")),
        }
        self.current_noise_config = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass

    def _find_ffmpeg(self):
        """Locates ffmpeg executable cross-platform, auto-installing if missing when package manager exists."""
        cmd = shutil.which("ffmpeg")
        if cmd:
            return cmd
        for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", "ffmpeg.exe"]:
            if os.path.exists(p):
                return p
        
        # Try auto-install if package manager exists
        self.ensure_ffmpeg_installed()
        return shutil.which("ffmpeg") or "ffmpeg"

    def _find_ffplay(self):
        """Locates ffplay executable cross-platform."""
        cmd = shutil.which("ffplay")
        if cmd:
            return cmd
        for p in ["/opt/homebrew/bin/ffplay", "/usr/local/bin/ffplay", "/usr/bin/ffplay", "C:\\ffmpeg\\bin\\ffplay.exe", "ffplay.exe"]:
            if os.path.exists(p):
                return p
        return None

    def ensure_ffmpeg_installed(self) -> bool:
        """Checks if ffmpeg/ffplay is available and logs recommendations if missing."""
        if shutil.which("ffmpeg") or shutil.which("ffplay"):
            return True

        logger.info("[AudioPlayer] Hinweis: 'ffmpeg' / 'ffplay' wurde im System-Pfad nicht gefunden.")
        logger.info("[AudioPlayer] Für optimale Audio-Wiedergabe wird die Installation von ffmpeg empfohlen:")
        if sys.platform == "darwin":
            logger.info("  -> macOS (Homebrew): brew install ffmpeg")
        elif sys.platform == "win32":
            logger.info("  -> Windows (winget): winget install Gnumeric.ffmpeg")
        else:
            logger.info("  -> Linux (Debian/Ubuntu): sudo apt-get install ffmpeg")
        return False

    def sync_noise(self, mask_noise: bool = False, ambient_noise: bool = False, balance: float = 0.0, 
                   noise_volume: float = 0.4, ambient_type: str = "noise", ambient_volume: float = 0.3):
        """
        Synchronizes continuous background noise (Vertäubung or Störschall).
        Runs continuously until config changes or noise is turned off.
        """
        with self._lock:
            target_mode = "off"
            target_side = "both"
            target_vol = 0.4
            target_file = self.noise_file

            if mask_noise:
                target_mode = "masking"
                if balance < 0:
                    target_side = "right"  # Speech is on Left (CI), Noise is on Right (Healthy ear)
                elif balance > 0:
                    target_side = "left"   # Speech is on Right (CI), Noise is on Left (Healthy ear)
                else:
                    target_side = "right"  # Fallback: Noise on Right ear so it never plays on both ears
                target_vol = noise_volume
                target_file = self.noise_file
            elif ambient_noise:
                target_mode = "ambient"
                target_side = "both"
                target_vol = ambient_volume
                target_file = self.ambient_files.get(ambient_type, self.noise_file)

            if not os.path.exists(target_file):
                target_file = self.noise_file

            new_config = (target_mode, target_side, target_vol, target_file)
            if new_config == self.current_noise_config and hasattr(self, "noise_process") and self.noise_process and self.noise_process.poll() is None:
                return

            if target_mode == "off" or not os.path.exists(target_file):
                self.stop_noise()
                return

            # Keep reference to old processes for seamless overlap
            old_processes = list(getattr(self, "noise_processes", []))

            ffplay_bin = self._find_ffplay()
            
            # Filter specification for stereo panning
            if target_side == "right":
                filter_str = f"volume={target_vol},pan=stereo|c0=0*c0|c1=c0+c1"
            elif target_side == "left":
                filter_str = f"volume={target_vol},pan=stereo|c0=c0+c1|c1=0*c0"
            else:
                filter_str = f"volume={target_vol * 1.5},pan=stereo|c0=c0|c1=c1"

            new_processes = []
            if ffplay_bin:
                cmd_noise = [
                    ffplay_bin, "-nodisp", "-loglevel", "quiet", "-loop", "0",
                    "-af", filter_str, target_file
                ]
                p = subprocess.Popen(cmd_noise, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                new_processes.append(p)
                self.noise_process = p
            else:
                ffmpeg_bin = self._find_ffmpeg()
                cmd_noise = [
                    ffmpeg_bin, "-loglevel", "quiet", "-re", "-stream_loop", "-1", "-i", target_file,
                    "-af", filter_str, "-f", "wav", "pipe:1"
                ]
                if sys.platform == "darwin":
                    cmd_play = ["afplay", "-"]
                elif sys.platform == "win32":
                    cmd_play = [self._find_ffplay() or "ffplay.exe", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"]
                else:
                    cmd_play = ["aplay"]
                
                p1 = subprocess.Popen(cmd_noise, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                p2 = subprocess.Popen(cmd_play, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                if p1.stdout:
                    p1.stdout.close()
                new_processes.extend([p1, p2])
                self.noise_process = p2

            self.noise_processes = new_processes
            self.current_noise_config = new_config

            # Terminate old processes after a short overlap to prevent audio dropouts
            if old_processes:
                threading.Thread(target=self._terminate_processes, args=(old_processes,), daemon=True).start()

    def _terminate_processes(self, procs):
        import time
        time.sleep(0.12)
        for p in procs:
            if p and p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=0.2)
                except Exception:
                    try:
                        p.kill()
                    except Exception:
                        pass

    def stop_noise(self):
        """Stops background continuous noise process cleanly."""
        procs = list(getattr(self, "noise_processes", []))
        if hasattr(self, "noise_process") and self.noise_process and self.noise_process not in procs:
            procs.append(self.noise_process)
        self.noise_processes = []
        self.noise_process = None
        self.current_noise_config = None

        for p in procs:
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        for p in procs:
            if p and p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
    def _get_calibration_file(self, signal_type: str = "speech_noise") -> str:
        """Returns path to calibration signal (speech noise or generated 1 kHz sine tone)."""
        if signal_type == "tone_1khz":
            os.makedirs(".cache/audio", exist_ok=True)
            calib_file = os.path.abspath(".cache/audio/calib_tone_1khz.wav")
            if not os.path.exists(calib_file) or os.path.getsize(calib_file) < 1000:
                import wave
                import struct
                import math
                sample_rate = 44100
                duration = 3.0
                num_samples = int(sample_rate * duration)
                with wave.open(calib_file, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    raw = bytearray()
                    for i in range(num_samples):
                        val = int(3276 * math.sin(2.0 * math.pi * 1000.0 * (i / sample_rate)))
                        raw.extend(struct.pack("<h", max(-32768, min(32767, val))))
                    wf.writeframes(raw)
            return calib_file
        else:
            return self.noise_file

    def start_calibration(self, signal_type: str = "speech_noise", volume: float = 0.5):
        """
        Starts continuous calibration signal playback via system audio backend.
        Ensures signal reaches headphones / CI on the same output device as exercises.
        """
        calib_file = self._get_calibration_file(signal_type)
        with self._lock:
            target_mode = "calibration"
            target_side = "both"
            target_vol = volume
            target_file = calib_file

            new_config = (target_mode, target_side, target_vol, target_file)
            if new_config == self.current_noise_config and hasattr(self, "noise_process") and self.noise_process and self.noise_process.poll() is None:
                return

            self.stop_noise()

            old_processes = list(getattr(self, "noise_processes", []))
            ffplay_bin = self._find_ffplay()
            filter_str = f"volume={target_vol * 1.5},pan=stereo|c0=c0|c1=c1"

            new_processes = []
            if ffplay_bin:
                cmd_noise = [
                    ffplay_bin, "-nodisp", "-loglevel", "quiet", "-loop", "0",
                    "-af", filter_str, target_file
                ]
                p = subprocess.Popen(cmd_noise, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                new_processes.append(p)
                self.noise_process = p
            else:
                ffmpeg_bin = self._find_ffmpeg()
                cmd_noise = [
                    ffmpeg_bin, "-loglevel", "quiet", "-re", "-stream_loop", "-1", "-i", target_file,
                    "-af", filter_str, "-f", "wav", "pipe:1"
                ]
                if sys.platform == "darwin":
                    cmd_play = ["afplay", "-"]
                elif sys.platform == "win32":
                    cmd_play = [self._find_ffplay() or "ffplay.exe", "-nodisp", "-autoexit", "-loglevel", "quiet", "-"]
                else:
                    cmd_play = ["aplay"]
                
                p1 = subprocess.Popen(cmd_noise, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                p2 = subprocess.Popen(cmd_play, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                if p1.stdout:
                    p1.stdout.close()
                new_processes.extend([p1, p2])
                self.noise_process = p2

            self.noise_processes = new_processes
            self.current_noise_config = new_config

            if old_processes:
                threading.Thread(target=self._terminate_processes, args=(old_processes,), daemon=True).start()

    def stop_calibration(self):
        """Stops calibration audio playback."""
        self.stop_noise()

    def stop_speech(self):
        """Stops speech process."""
        if self.speech_process and self.speech_process.poll() is None:
            try:
                self.speech_process.terminate()
            except Exception:
                pass
            self.speech_process = None

    def stop(self):
        """Stops both speech and noise processes."""
        self.stop_speech()
        self.stop_noise()

    def play(self, file_path: str, balance: float = 0.0, volume: float = 1.0, rate: float = 1.0, 
             mask_noise: bool = False, noise_volume: float = 0.4, 
             ambient_noise: bool = False, ambient_type: str = "noise", ambient_volume: float = 0.3,
             freq_filter: str = "none", wait_until_done: bool = False):
        """
        Plays an audio file cross-platform while continuous noise runs.
        Supports frequency filtering (highpass, high_boost, lowpass) and stereo panning.
        """
        self.stop_speech()
        
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            logger.error(f"[AudioPlayer] File not found: {file_path}")
            return

        # Ensure continuous noise is synced and running
        self.sync_noise(mask_noise=mask_noise, ambient_noise=ambient_noise, ambient_type=ambient_type, balance=balance, 
                       noise_volume=noise_volume, ambient_volume=ambient_volume)

        def _play_thread():
            try:
                ffmpeg_path = self._find_ffmpeg()
                play_path = file_path

                # Apply audio filters (frequency equalizer & stereo panning)
                filter_parts = []
                if freq_filter == "highpass":
                    filter_parts.append("highpass=f=1500")
                elif freq_filter == "high_boost":
                    filter_parts.append("equalizer=f=3500:width_type=q:width=1.0:g=12,treble=g=8:f=3000")
                elif freq_filter == "lowpass":
                    filter_parts.append("lowpass=f=1000")

                if balance < 0:
                    filter_parts.append(f"volume={volume},pan=stereo|c0=c0+c1|c1=0*c0")
                elif balance > 0:
                    filter_parts.append(f"volume={volume},pan=stereo|c0=0*c0|c1=c0+c1")
                elif volume != 1.0:
                    filter_parts.append(f"volume={volume}")

                if filter_parts:
                    filter_str = ",".join(filter_parts)
                    os.makedirs(".cache/audio", exist_ok=True)
                    temp_speech = os.path.join(".cache/audio", f"temp_{uuid.uuid4().hex[:8]}_speech.wav")
                    cmd_filter = [
                        ffmpeg_path, "-y", "-i", file_path,
                        "-af", filter_str, temp_speech
                    ]
                    res = subprocess.run(cmd_filter, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                    if res.returncode == 0 and os.path.exists(temp_speech):
                        play_path = temp_speech

                # Playback command per OS
                vol_val = str(max(0.1, min(3.0, volume)))
                
                if sys.platform == "darwin":
                    cmd_play = ["afplay", "-v", vol_val, "-r", str(rate), play_path]
                elif sys.platform == "win32":
                    ffplay_bin = self._find_ffplay() or "ffplay.exe"
                    cmd_play = [ffplay_bin, "-nodisp", "-autoexit", "-loglevel", "quiet", play_path]
                else:
                    ffplay_bin = self._find_ffplay() or shutil.which("paplay") or shutil.which("aplay")
                    if ffplay_bin and "ffplay" in ffplay_bin:
                        cmd_play = [ffplay_bin, "-nodisp", "-autoexit", "-loglevel", "quiet", play_path]
                    else:
                        cmd_play = [ffplay_bin or "aplay", play_path]

                self.speech_process = subprocess.Popen(cmd_play, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                self.speech_process.wait()

                if play_path != file_path and os.path.exists(play_path):
                    try:
                        os.remove(play_path)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"[AudioPlayer] Playback error: {e}")

        t = threading.Thread(target=_play_thread, daemon=True)
        t.start()
        if wait_until_done:
            t.join()
