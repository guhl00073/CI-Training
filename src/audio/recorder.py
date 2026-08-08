import subprocess
import os
import signal
import tempfile
import pathlib
import time

class AudioRecorder:
    """
    Microphone Recorder Engine for Speech-to-Text / Repeat-after-me exercises.
    Captures user voice input to a WAVE file.
    """
    def __init__(self):
        self.process = None
        self.output_file = None
        self.is_recording = False

    def record_clip(self, duration_sec: float = 3.0) -> str:
        """
        Records a clip from default audio input for duration_sec seconds.
        Returns the path to the output WAV file.
        """
        self.output_file = tempfile.mktemp(suffix=".wav")
        ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        
        if os.path.exists(ffmpeg_path):
            cmd = [
                ffmpeg_path, "-y", "-f", "avfoundation", "-i", ":0",
                "-t", str(duration_sec), "-ar", "16000", "-ac", "1", self.output_file
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self.output_file
            except Exception as e:
                print(f"[AudioRecorder] Recording error: {e}")
        return None

    def start_recording(self, duration_sec: float = 5.0) -> str:
        """Starts background recording from microphone."""
        self.stop_recording()
        self.output_file = tempfile.mktemp(suffix=".wav")
        self.is_recording = True

        ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        if os.path.exists(ffmpeg_path):
            cmd = [
                ffmpeg_path, "-y", "-f", "avfoundation", "-i", ":0",
                "-t", str(duration_sec), "-ar", "16000", "-ac", "1", self.output_file
            ]
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
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
