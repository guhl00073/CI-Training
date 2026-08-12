import os
import subprocess
import urllib.request
import urllib.parse
import json
import hashlib
import tempfile
import pathlib
import platform
import sys

class TTSEngine:
    """
    Multi-Provider Text-to-Speech Engine with voice selection.
    Cross-platform support for macOS (native `say`), Windows (PowerShell SAPI5),
    and Linux (`espeak` / `gTTS`), guaranteeing authentic German pronunciation (de_DE).
    """
    AVAILABLE_VOICES = [
        {"id": "Anna", "name": "Anna (Weiblich - Deutsch)", "gender": "weiblich", "say_id": "Anna", "pitch": 1.00, "tempo": 1.00},
        {"id": "Eddy", "name": "Eddy (Männlich - Deutsch)", "gender": "männlich", "say_id": "Eddy (Deutsch (Deutschland))", "pitch": 0.76, "tempo": 1.30},
        {"id": "Flo", "name": "Flo (Männlich - Deutsch)", "gender": "männlich", "say_id": "Flo (Deutsch (Deutschland))", "pitch": 0.84, "tempo": 1.18},
        {"id": "Rocko", "name": "Rocko (Männlich - Deutsch)", "gender": "männlich", "say_id": "Rocko (Deutsch (Deutschland))", "pitch": 0.68, "tempo": 1.45},
        {"id": "Sandy", "name": "Sandy (Weiblich - Deutsch)", "gender": "weiblich", "say_id": "Sandy (Deutsch (Deutschland))", "pitch": 1.14, "tempo": 0.88},
        {"id": "Shelley", "name": "Shelley (Weiblich - Deutsch)", "gender": "weiblich", "say_id": "Shelley (Deutsch (Deutschland))", "pitch": 1.05, "tempo": 0.95},
        {"id": "Grandpa", "name": "Grandpa (Senior Männlich)", "gender": "männlich", "say_id": "Grandpa (Deutsch (Deutschland))", "pitch": 0.72, "tempo": 1.10},
        {"id": "Grandma", "name": "Grandma (Senior Weiblich)", "gender": "weiblich", "say_id": "Grandma (Deutsch (Deutschland))", "pitch": 0.92, "tempo": 0.90}
    ]

    def __init__(self, cache_dir: str = ".cache/audio"):
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup_cache()

    def cleanup_cache(self, max_age_days: float = 7.0, max_size_mb: float = 100.0) -> int:
        """Purges old or excessive cached audio files to prevent disk bloat."""
        if not self.cache_dir.exists():
            return 0

        import time
        now = time.time()
        max_age_sec = max_age_days * 86400.0
        max_bytes = max_size_mb * 1024 * 1024
        removed_count = 0

        files = [f for f in self.cache_dir.iterdir() if f.is_file()]
        # Sort by mtime ascending (oldest first)
        files.sort(key=lambda f: f.stat().st_mtime)

        # 1. Purge files older than max_age_days
        remaining = []
        for f in files:
            try:
                stat = f.stat()
                if (now - stat.st_mtime) > max_age_sec:
                    f.unlink()
                    removed_count += 1
                else:
                    remaining.append((f, stat.st_size))
            except Exception:
                pass

        # 2. Enforce total size limit (max_size_mb)
        total_size = sum(size for _, size in remaining)
        for f, size in remaining:
            if total_size <= max_bytes:
                break
            try:
                f.unlink()
                total_size -= size
                removed_count += 1
            except Exception:
                pass

        return removed_count

    def _get_cache_path(self, text: str, voice: str, rate: float) -> pathlib.Path:
        key = f"{text}_{voice}_{rate}"
        file_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"tts_{file_hash}.mp3"

    def generate_audio(self, text: str, rate: float = 1.0, voice: str = "Anna") -> str:
        """
        Synthesizes speech for the given text using German locale across macOS, Windows, and Linux.
        Prioritizes Google TTS online for highest quality, falling back to native TTS offline.
        Ensures full articulation of trailing consonants (s, z, t, ch) without truncation.
        """
        if not text:
            return None

        clean_text = text.strip()
        speech_text = clean_text if clean_text.endswith(('.', '!', '?', ';', ':')) else f"{clean_text}."

        cache_path = self._get_cache_path(speech_text, voice, rate)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            return str(cache_path)

        # Primary: Google TTS Online (highest quality, identical across platforms)
        google_res = self._generate_google_tts(speech_text, str(cache_path), voice=voice)
        if google_res and os.path.exists(google_res) and os.path.getsize(google_res) > 0:
            return google_res

        # Fallback for offline mode: OS native dispatch
        if platform.system() == "Darwin":
            return self._generate_mac_say(speech_text, rate, voice, str(cache_path))
        elif platform.system() == "Windows":
            return self._generate_windows_sapi(speech_text, rate, voice, str(cache_path))
        else:
            return self._generate_linux_tts(speech_text, rate, voice, str(cache_path))

    def _generate_windows_sapi(self, text: str, rate: float, voice: str, output_path: str) -> str:
        """Windows PowerShell SAPI5 speech synthesis."""
        try:
            ps_script = f"""
            Add-Type -AssemblyName System.Speech;
            $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
            $synth.SetOutputToWaveFile('{output_path}');
            $synth.Speak('{text}');
            $synth.Dispose();
            """
            subprocess.run(["powershell", "-Command", ps_script], check=True, stderr=subprocess.DEVNULL)
            if os.path.exists(output_path):
                return output_path
        except Exception as e:
            print(f"[TTSEngine] Windows SAPI notice: {e}")

        return self._generate_google_tts(text, output_path, voice=voice)

    def _generate_linux_tts(self, text: str, rate: float, voice: str, output_path: str) -> str:
        """Linux google_tts (neural quality) with espeak fallback."""
        google_res = self._generate_google_tts(text, output_path, voice=voice)
        if google_res and os.path.exists(google_res) and os.path.getsize(google_res) > 0:
            return google_res

        try:
            cmd = ["espeak", "-v", "de", "-w", output_path, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            if os.path.exists(output_path):
                return output_path
        except Exception:
            pass
        return None

    def _generate_google_tts(self, text: str, output_path: str, voice: str = "Anna") -> str:
        if os.environ.get("CI_TRAINER_OFFLINE") == "1":
            return None

        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl=de&client=tw-ob"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = response.read()
                    if len(data) > 0:
                        with open(output_path, 'wb') as f:
                            f.write(data)

                        # Apply distinct voice profile pitch/tempo transformation
                        voice_entry = next((v for v in self.AVAILABLE_VOICES if v["id"] == voice or v["say_id"] == voice), None)
                        if voice_entry:
                            pitch = voice_entry.get("pitch", 1.0)
                            tempo = voice_entry.get("tempo", 1.0)
                            if pitch != 1.0 or tempo != 1.0:
                                import shutil
                                ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
                                if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                                    temp_output = output_path + ".tmp.mp3"
                                    filter_str = f"asetrate=24000*{pitch},aresample=24000,atempo={tempo}"
                                    cmd_pitch = [
                                        ffmpeg_bin, "-y", "-i", output_path,
                                        "-af", filter_str,
                                        temp_output
                                    ]
                                    res = subprocess.run(cmd_pitch, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    if res.returncode == 0 and os.path.exists(temp_output):
                                        os.replace(temp_output, output_path)

                        return output_path
        except BaseException as e:
            print(f"[TTSEngine] Google TTS fallback notice: {e}")
        return None

    def _generate_mac_say(self, text: str, rate: float = 1.0, voice: str = "Anna", output_path: str = None) -> str:
        words_per_min = int(175 * rate)
        if not output_path:
            output_path = str(self.cache_dir / "mac_speech.mp3")

        voice_entry = next((v for v in self.AVAILABLE_VOICES if v["id"] == voice or v["say_id"] == voice), None)
        say_voice = voice_entry["say_id"] if voice_entry else "Anna"

        temp_aiff = output_path + ".temp.aiff"
        try:
            cmd = ["say", "-v", say_voice, "-r", str(words_per_min), "-o", temp_aiff, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        except Exception:
            cmd = ["say", "-v", "Anna", "-r", str(words_per_min), "-o", temp_aiff, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

        if os.path.exists(temp_aiff):
            import shutil
            ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
            if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                cmd_pad = [
                    ffmpeg_bin, "-y", "-i", temp_aiff,
                    "-af", "apad=pad_dur=0.35",
                    output_path
                ]
                res = subprocess.run(cmd_pad, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0 and os.path.exists(output_path):
                    if os.path.exists(temp_aiff):
                        os.remove(temp_aiff)
                    return output_path
            os.replace(temp_aiff, output_path)

        return output_path

    def get_voices(self):
        return self.AVAILABLE_VOICES
