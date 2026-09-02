import subprocess
import os
import signal
import tempfile
import pathlib
import time
import sys
import shutil

from src.utils.paths import get_subprocess_flags
from src.utils.paths import get_user_data_dir
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """
    Microphone Recorder Engine for Speech-to-Text / Repeat-after-me exercises.
    Captures user voice input cross-platform (macOS, Windows, Linux) to a WAVE file.
    """
    def __init__(self):
        self.process = None
        self.output_file = None
        self.is_recording = False

    def _find_ffmpeg(self) -> str:
        cmd = shutil.which("ffmpeg")
        if cmd:
            return cmd
        for p in [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/usr/bin/ffmpeg",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "ffmpeg.exe"
        ]:
            if os.path.exists(p):
                return p
        return None

    def _get_input_args(self) -> list:
        if sys.platform == "darwin":
            return ["-f", "avfoundation", "-i", ":0"]
        elif sys.platform == "win32":
            return ["-f", "dshow", "-i", "audio=default"]
        else:
            return ["-f", "alsa", "-i", "default"]

    def _create_temp_wav(self) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        return path

    def record_clip(self, duration_sec: float = 3.0) -> str:
        """
        Records a clip from default audio input for duration_sec seconds.
        Returns the path to the output WAV file.
        """
        self.output_file = self._create_temp_wav()
        ffmpeg_path = self._find_ffmpeg()

        if ffmpeg_path:
            input_args = self._get_input_args()
            cmd = [
                ffmpeg_path, "-y", *input_args,
                "-t", str(duration_sec), "-ar", "16000", "-ac", "1", self.output_file
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                return self.output_file
            except Exception as e:
                logger.error(f"[AudioRecorder] Recording error: {e}")
        return None

    def start_recording(self, duration_sec: float = 5.0) -> str:
        """Starts background recording from microphone."""
        self.stop_recording()
        self.output_file = self._create_temp_wav()
        self.is_recording = True

        ffmpeg_path = self._find_ffmpeg()
        if ffmpeg_path:
            input_args = self._get_input_args()
            cmd = [
                ffmpeg_path, "-y", *input_args,
                "-t", str(duration_sec), "-ar", "16000", "-ac", "1", self.output_file
            ]
            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags()
                )
            except Exception as e:
                logger.error(f"[AudioRecorder] Start recording error: {e}")
                self.is_recording = False
        return self.output_file

    def stop_recording(self) -> str:
        """Stops recording and returns the path to the recorded WAV file."""
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=2.0)
            except Exception:
                self.process.kill()
        self.is_recording = False
        return self.output_file

