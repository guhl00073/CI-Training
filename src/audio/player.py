import subprocess
import os
import tempfile
import pathlib
import threading
import sys
import shutil
import atexit

class AudioPlayer:
    """
    Audio Player Engine tailored for Cochlear Implant (CI) users.
    Supports macOS, Windows, and Linux cross-platform execution.
    Features stereo panning, speech rate, continuous contralateral masking, and Störschall noise.
    """
    def __init__(self, noise_file: str = "data/rauschen.mp3"):
        self.speech_process = None
        self.noise_process = None
        self.noise_processes = []
        self.noise_file = os.path.abspath(noise_file)
        data_dir = os.path.dirname(self.noise_file)
        self.ambient_files = {
            "noise":      self.noise_file,
            "restaurant": os.path.join(data_dir, "ambient_restaurant.wav"),
            "cafe":       os.path.join(data_dir, "ambient_restaurant.wav"),
            "traffic":    os.path.join(data_dir, "ambient_traffic.wav"),
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

    def ensure_ffmpeg_installed(self):
        """Automatically attempts to install ffmpeg/ffplay if missing and package manager is available."""
        if shutil.which("ffmpeg") or shutil.which("ffplay"):
            return True

        print("[AudioPlayer] ffmpeg/ffplay nicht gefunden. Versuche automatische Installation...")
        try:
            if sys.platform == "darwin" and shutil.which("brew"):
                subprocess.run(["brew", "install", "ffmpeg"], check=True)
                return True
            elif sys.platform == "win32" and shutil.which("winget"):
                subprocess.run(["winget", "install", "Gnumeric.ffmpeg", "--accept-source-agreements", "--accept-package-agreements"], check=False)
                return True
            elif sys.platform.startswith("linux"):
                if shutil.which("apt-get"):
                    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=False)
                    return True
        except Exception as e:
            print(f"[AudioPlayer] Automatische Installation fehlgeschlagen: {e}")
        return False

    def sync_noise(self, mask_noise: bool = True, ambient_noise: bool = False, balance: float = 0.0, 
                   noise_volume: float = 0.4, ambient_type: str = "noise", ambient_volume: float = 0.3):
        """
        Synchronizes continuous background noise (Vertäubung or Störschall).
        Runs continuously until config changes or noise is turned off.
        """
        with self._lock:
            target_mode = "off"
            target_side = "both"
            target_vol = 0.4

            if mask_noise:
                target_mode = "masking"
                if balance < 0:
                    target_side = "right"
                elif balance > 0:
                    target_side = "left"
                else:
                    target_side = "both"
                target_vol = noise_volume
            elif ambient_noise:
                target_mode = "ambient"
                target_side = "both"
                target_vol = ambient_volume

            target_file = self.ambient_files.get(ambient_type, self.noise_file)
            if not os.path.exists(target_file):
                target_file = self.noise_file

            new_config = (target_mode, target_side, target_vol, target_file)
            if new_config == self.current_noise_config:
                return

            self.stop_noise()
            self.current_noise_config = new_config

            if target_mode == "off" or not os.path.exists(target_file):
                return

            ffplay_bin = self._find_ffplay()
            
            # Filter specification for stereo panning
            if target_side == "right":
                filter_str = f"volume={target_vol},pan=stereo|c0=0*c0|c1=c0+c1"
            elif target_side == "left":
                filter_str = f"volume={target_vol},pan=stereo|c0=c0+c1|c1=0*c0"
            else:
                filter_str = f"volume={target_vol * 1.5},pan=stereo|c0=c0|c1=c1"

            self.noise_processes = []
            if ffplay_bin:
                cmd_noise = [
                    ffplay_bin, "-nodisp", "-loglevel", "quiet", "-loop", "0",
                    "-af", filter_str, target_file
                ]
                p = subprocess.Popen(cmd_noise, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.noise_processes.append(p)
                self.noise_process = p
            else:
                ffmpeg_bin = self._find_ffmpeg()
                cmd_noise = [
                    ffmpeg_bin, "-loglevel", "quiet", "-re", "-stream_loop", "-1", "-i", target_file,
                    "-af", filter_str, "-f", "wav", "pipe:1"
                ]
                if sys.platform == "darwin":
                    cmd_play = ["afplay", "-"]
                else:
                    cmd_play = ["aplay"]
                
                p1 = subprocess.Popen(cmd_noise, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                p2 = subprocess.Popen(cmd_play, stdin=p1.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if p1.stdout:
                    p1.stdout.close()
                self.noise_processes.extend([p1, p2])
                self.noise_process = p2

    def stop_noise(self):
        """Stops background continuous noise process cleanly."""
        if hasattr(self, "noise_processes") and self.noise_processes:
            for p in self.noise_processes:
                if p and p.poll() is None:
                    try:
                        p.terminate()
                        p.wait(timeout=0.3)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
            self.noise_processes = []
        if hasattr(self, "noise_process") and self.noise_process:
            if self.noise_process.poll() is None:
                try:
                    self.noise_process.terminate()
                except Exception:
                    pass
            self.noise_process = None
        self.current_noise_config = None

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
             mask_noise: bool = True, noise_volume: float = 0.4, 
             ambient_noise: bool = False, ambient_type: str = "noise", ambient_volume: float = 0.3,
             wait_until_done: bool = False):
        """
        Plays an audio file cross-platform while continuous noise runs.
        Supports asynchronous or synchronous (wait_until_done=True) playback.
        """
        self.stop_speech()
        
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            print(f"[AudioPlayer] File not found: {file_path}")
            return

        # Ensure continuous noise is synced and running
        self.sync_noise(mask_noise=mask_noise, ambient_noise=ambient_noise, ambient_type=ambient_type, balance=balance, 
                       noise_volume=noise_volume, ambient_volume=ambient_volume)

        def _play_thread():
            try:
                ffmpeg_path = self._find_ffmpeg()
                play_path = file_path

                # Apply strict panning to speech audio if balance is set
                if balance != 0.0:
                    temp_speech = tempfile.mktemp(suffix="_speech.wav", dir=".cache/audio")
                    os.makedirs(".cache/audio", exist_ok=True)
                    if balance < 0:
                        filter_str = f"volume={volume},pan=stereo|c0=c0+c1|c1=0*c0"
                    else:
                        filter_str = f"volume={volume},pan=stereo|c0=0*c0|c1=c0+c1"

                    cmd_pan = [
                        ffmpeg_path, "-y", "-i", file_path,
                        "-af", filter_str, temp_speech
                    ]
                    res = subprocess.run(cmd_pan, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0 and os.path.exists(temp_speech):
                        play_path = temp_speech

                # Playback command per OS
                vol_val = str(max(0.1, min(1.0, volume)))
                
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

                self.speech_process = subprocess.Popen(cmd_play, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.speech_process.wait()

            except Exception as e:
                print(f"[AudioPlayer] Playback error: {e}")

        t = threading.Thread(target=_play_thread, daemon=True)
        t.start()
        if wait_until_done:
            t.join()
