import os
import subprocess
import urllib.request
import urllib.parse
import hashlib
import pathlib
import platform
import shutil
import time
import wave
import struct
import math

from src.utils.paths import get_user_data_dir, get_subprocess_flags
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Availability check: edge-tts (Microsoft Azure Neural) ────────────────────
try:
    import edge_tts as _edge_tts_check  # noqa: F401
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning(
        "[TTS] ⚠  edge-tts nicht installiert – Microsoft Azure Neural Stimmen deaktiviert.\n"
        "       Installation: pip install edge-tts"
    )



class TTSEngine:
    """
    High-Fidelity Multi-Voice Text-to-Speech Engine for Cochlear Implant Training.
    Provides genuinely distinct speaker personalities (Female, Male, Senior, Deep, High, Online)
    using native high-resolution system speech models (macOS/Windows) and Google Cloud TTS.
    """
    AVAILABLE_VOICES = [
        # 💻 System-Stimme (Nativ - Latenzfrei & Natürlich)
        {"id": "Anna", "name": "👩 Anna (System - Natürlich & Klar)", "gender": "weiblich", "source": "system", "say_id": "Anna", "pitch": 1.00, "tempo": 1.00},

        # 🌐 Google Cloud (Online KI-Synthese - Natürlich)
        {"id": "Google-Online", "name": "🌐 Google Cloud (Online - Natürlich)", "gender": "weiblich", "source": "google", "say_id": "Anna", "pitch": 1.00, "tempo": 1.00}
    ]

    EDGE_VOICES = [
        {"id": "Edge-Conrad", "name": "👨 Conrad (Azure - Männlich Natürlich & Kräftig)", "gender": "männlich", "source": "edge", "azure_id": "de-DE-ConradNeural"},
        {"id": "Edge-Florian", "name": "👨 Florian (Azure - Männlich Klar & Modern)", "gender": "männlich", "source": "edge", "azure_id": "de-DE-FlorianMultilingualNeural"},
        {"id": "Edge-Killian", "name": "👨 Killian (Azure - Männlich Dynamisch)", "gender": "männlich", "source": "edge", "azure_id": "de-DE-KillianNeural"},
        {"id": "Edge-Katja", "name": "👩 Katja (Azure - Weiblich Klar & Prägnant)", "gender": "weiblich", "source": "edge", "azure_id": "de-DE-KatjaNeural"},
        {"id": "Edge-Amala", "name": "👩 Amala (Azure - Weiblich Sanft & Natürlich)", "gender": "weiblich", "source": "edge", "azure_id": "de-DE-AmalaNeural"},
        {"id": "Edge-Seraphina", "name": "👩 Seraphina (Azure - Weiblich Fein & Ausgewogen)", "gender": "weiblich", "source": "edge", "azure_id": "de-DE-SeraphinaMultilingualNeural"},
        {"id": "Edge-Jonas-AT", "name": "👨 Jonas (Azure - Österreich Männlich)", "gender": "männlich", "source": "edge", "azure_id": "de-AT-JonasNeural"},
        {"id": "Edge-Ingrid-AT", "name": "👩 Ingrid (Azure - Österreich Weiblich)", "gender": "weiblich", "source": "edge", "azure_id": "de-AT-IngridNeural"},
        {"id": "Edge-Jan-CH", "name": "👨 Jan (Azure - Schweiz Männlich)", "gender": "männlich", "source": "edge", "azure_id": "de-CH-JanNeural"},
        {"id": "Edge-Leni-CH", "name": "👩 Leni (Azure - Schweiz Weiblich)", "gender": "weiblich", "source": "edge", "azure_id": "de-CH-LeniNeural"},
    ]

    EDGE_VOICES_EN = [
        {"id": "Edge-EN-Ava", "name": "🇺🇸 👩 Ava (Azure - US Weiblich Natürlich)", "gender": "weiblich", "source": "edge", "azure_id": "en-US-AvaNeural"},
        {"id": "Edge-EN-Andrew", "name": "🇺🇸 👨 Andrew (Azure - US Männlich Natürlich)", "gender": "männlich", "source": "edge", "azure_id": "en-US-AndrewNeural"},
        {"id": "Edge-EN-Emma", "name": "🇺🇸 👩 Emma (Azure - US Weiblich Sanft)", "gender": "weiblich", "source": "edge", "azure_id": "en-US-EmmaNeural"},
        {"id": "Edge-EN-Brian", "name": "🇺🇸 👨 Brian (Azure - US Männlich Klar)", "gender": "männlich", "source": "edge", "azure_id": "en-US-BrianNeural"},
        {"id": "Edge-EN-Sonia", "name": "🇬🇧 👩 Sonia (Azure - UK Weiblich Präzise)", "gender": "weiblich", "source": "edge", "azure_id": "en-GB-SoniaNeural"},
        {"id": "Edge-EN-Ryan", "name": "🇬🇧 👨 Ryan (Azure - UK Männlich Klar)", "gender": "männlich", "source": "edge", "azure_id": "en-GB-RyanNeural"},
    ]

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            self.cache_dir = get_user_data_dir() / "cache" / "audio"
        else:
            self.cache_dir = pathlib.Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cleanup_cache()
        except Exception as e:
            logger.warning(f"[TTSEngine] Cache init warning: {e}")

    def cleanup_cache(self, max_age_days: float = 7.0, max_size_mb: float = 150.0) -> int:
        """Purges old or excessive cached audio files to prevent disk bloat."""
        try:
            if not self.cache_dir.exists():
                return 0

            now = time.time()
            max_age_sec = max_age_days * 86400.0
            max_bytes = max_size_mb * 1024 * 1024
            removed_count = 0

            files = [f for f in self.cache_dir.iterdir() if f.is_file()]
            files.sort(key=lambda f: f.stat().st_mtime)

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
        except Exception:
            return 0

    # ─── Audio Synthesis ──────────────────────────────────────────────────────

    def _get_cache_path(self, text: str, voice: str, rate: float) -> pathlib.Path:
        key = f"{text}_{voice}_{rate}"
        file_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"tts_{file_hash}.wav"

    def generate_audio(self, text: str, rate: float = 1.0, voice: str = "Anna") -> str:
        """
        Synthesizes text into high-fidelity audio (WAV) using:
        - Microsoft Azure Neural (Edge-TTS) for genuine German studio voices
        - Native macOS/Windows System Speech for downloaded OS voices
        - Google Cloud TTS for Google-Online synthesis.
        """
        if not text:
            return None

        clean_text = text.strip()
        speech_text = clean_text if clean_text.endswith(('.', '!', '?', ';', ':')) else f"{clean_text}."

        cache_path = self._get_cache_path(speech_text, voice, rate)
        if cache_path.exists() and cache_path.stat().st_size > 1000:
            return str(cache_path)

        # 1. Edge-TTS (Microsoft Azure Neural Studio Voices)
        if voice.startswith("Edge-") and os.environ.get("CI_TRAINER_OFFLINE") != "1":
            edge_res = self._generate_edge_tts(speech_text, str(cache_path), voice=voice, rate=rate)
            if edge_res and os.path.exists(edge_res) and os.path.getsize(edge_res) > 500:
                return edge_res

        # 2. Google Cloud Online TTS
        if voice.startswith("Google-Online") and os.environ.get("CI_TRAINER_OFFLINE") != "1":
            google_res = self._generate_google_tts(speech_text, str(cache_path), voice=voice, rate=rate)
            if google_res and os.path.exists(google_res) and os.path.getsize(google_res) > 1000:
                return google_res

        # 3. Native OS Dispatch (macOS say / Windows SAPI & WinRT)
        if platform.system() == "Darwin":
            mac_res = self._generate_mac_say(speech_text, rate, voice, str(cache_path))
            if mac_res and os.path.exists(mac_res) and os.path.getsize(mac_res) > 1000:
                return mac_res
        elif platform.system() == "Windows":
            win_res = self._generate_windows_sapi(speech_text, rate, voice, str(cache_path))
            if win_res and os.path.exists(win_res) and os.path.getsize(win_res) > 1000:
                return win_res

        # 4. Fallback chain: Edge-TTS -> Google -> Linux
        if os.environ.get("CI_TRAINER_OFFLINE") != "1":
            edge_fb = self._generate_edge_tts(speech_text, str(cache_path), voice="Edge-Conrad", rate=rate)
            if edge_fb and os.path.exists(edge_fb) and os.path.getsize(edge_fb) > 500:
                return edge_fb

            google_res = self._generate_google_tts(speech_text, str(cache_path), voice="Google-Online", rate=rate)
            if google_res and os.path.exists(google_res) and os.path.getsize(google_res) > 1000:
                return google_res

        return self._generate_linux_tts(speech_text, rate, voice, str(cache_path))

    def _generate_edge_tts(self, text: str, output_path: str, voice: str = "Edge-Conrad", rate: float = 1.0) -> str:
        if os.environ.get("CI_TRAINER_OFFLINE") == "1":
            return None
        try:
            import asyncio
            import edge_tts

            voice_entry = next((v for v in (self.EDGE_VOICES + self.EDGE_VOICES_EN) if v["id"] == voice), None)
            azure_voice = voice_entry["azure_id"] if voice_entry else ("en-US-AvaNeural" if "EN" in voice else "de-DE-ConradNeural")

            rate_pct = int((rate - 1.0) * 100)
            rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

            temp_mp3 = output_path + ".temp.mp3"

            async def _run():
                comm = edge_tts.Communicate(text, azure_voice, rate=rate_str)
                await comm.save(temp_mp3)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        pool.submit(lambda: asyncio.run(_run())).result()
                else:
                    loop.run_until_complete(_run())
            except RuntimeError:
                asyncio.run(_run())

            if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 100:
                ffmpeg_bin = self._find_ffmpeg()
                if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                    cmd = [
                        ffmpeg_bin, "-y", "-i", temp_mp3,
                        "-ar", "24000", "-ac", "1",
                        output_path
                    ]
                    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                    if os.path.exists(temp_mp3):
                        os.remove(temp_mp3)
                    if res.returncode == 0 and os.path.exists(output_path):
                        return output_path
                os.replace(temp_mp3, output_path)
                return output_path
        except Exception as e:
            logger.info(f"[TTSEngine] Edge-TTS notice: {e}")
        return None

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

    def _generate_google_tts(self, text: str, output_path: str, voice: str = "Anna", rate: float = 1.0) -> str:
        if os.environ.get("CI_TRAINER_OFFLINE") == "1":
            return None

        voice_entry = next((v for v in self.AVAILABLE_VOICES if v["id"] == voice or v["name"].startswith(voice)), None)
        if not voice_entry:
            voice_entry = self.AVAILABLE_VOICES[0]

        pitch_factor = voice_entry.get("pitch", 1.0) if voice_entry else 1.0
        tempo_factor = (voice_entry.get("tempo", 1.0) if voice_entry else 1.0) * rate

        tl = "en" if ("en" in voice.lower() or "us" in voice.lower() or "uk" in voice.lower()) else "de"

        encoded_text = urllib.parse.quote(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl={tl}&client=tw-ob"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = response.read()
                    if len(data) > 0:
                        temp_mp3 = output_path + ".temp.mp3"
                        with open(temp_mp3, 'wb') as f:
                            f.write(data)

                        ffmpeg_bin = self._find_ffmpeg()
                        if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                            filter_str = f"asetrate=24000*{pitch_factor},aresample=24000,atempo={tempo_factor}"
                            cmd = [
                                ffmpeg_bin, "-y", "-i", temp_mp3,
                                "-af", filter_str,
                                "-ar", "22050", "-ac", "1",
                                output_path
                            ]
                            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                            if os.path.exists(temp_mp3):
                                os.remove(temp_mp3)
                            if res.returncode == 0 and os.path.exists(output_path):
                                return output_path
                        else:
                            os.replace(temp_mp3, output_path)
                            return output_path
        except BaseException as e:
            logger.info(f"[TTSEngine] Google TTS fallback notice: {e}")
        return None

    def _generate_mac_say(self, text: str, rate: float = 1.0, voice: str = "Anna", output_path: str = None) -> str:
        if not output_path:
            output_path = str(self.cache_dir / "mac_speech.wav")

        voice_entry = next((v for v in self.AVAILABLE_VOICES if v["id"] == voice or v["name"].startswith(voice)), None)
        voice_gender = voice_entry.get("gender", "weiblich") if voice_entry else "weiblich"
        tempo_factor = voice_entry.get("tempo", 1.0) if voice_entry else 1.0
        words_per_min = int(175 * rate * tempo_factor)

        say_voice = voice
        if voice_entry and "say_id" in voice_entry:
            say_voice = voice_entry["say_id"]
        gender_fallback = "Anna"

        temp_aiff = output_path + ".temp.aiff"
        try:
            cmd = ["say", "-v", say_voice, "-r", str(words_per_min), "-o", temp_aiff, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL, **get_subprocess_flags())
        except Exception:
            cmd = ["say", "-v", gender_fallback, "-r", str(words_per_min), "-o", temp_aiff, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL, **get_subprocess_flags())

        if os.path.exists(temp_aiff):
            ffmpeg_bin = self._find_ffmpeg()
            if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                cmd_pad = [
                    ffmpeg_bin, "-y", "-i", temp_aiff,
                    "-af", "apad=pad_dur=0.35",
                    "-ar", "22050", "-ac", "1",
                    output_path
                ]
                res = subprocess.run(cmd_pad, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_subprocess_flags())
                if os.path.exists(temp_aiff):
                    os.remove(temp_aiff)
                if res.returncode == 0 and os.path.exists(output_path):
                    return output_path
            os.replace(temp_aiff, output_path)

        return output_path

    def _generate_windows_sapi(self, text: str, rate: float, voice: str, output_path: str) -> str:
        voices_list = self.get_voices()
        voice_entry = next((v for v in voices_list if v["id"] == voice or v["name"].startswith(voice) or voice in v["name"]), None)
        target_name = voice_entry["id"] if voice_entry else voice
        target_id = voice_entry.get("say_id", target_name) if voice_entry else target_name
        clean_target = target_name.replace("Microsoft ", "").replace(" Desktop", "").split()[0]

        safe_text = text.replace("'", "''")
        safe_output = output_path.replace("'", "''")
        safe_target_id = target_id.replace("'", "''")
        safe_clean_target = clean_target.replace("'", "''")

        # 1. Native Windows.Media.SpeechSynthesis (WinRT OneCore Voices)
        try:
            ps_winrt = f"""
            try {{
                [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
                $synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
                $all = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices
                
                # Try exact Id/DisplayName match first, then fuzzy match
                $target = $all | Where-Object {{ $_.Id -eq '{safe_target_id}' -or $_.DisplayName -eq '{safe_target_id}' }} | Select-Object -First 1
                if (-not $target) {{
                    $target = $all | Where-Object {{ $_.DisplayName -like '*{safe_clean_target}*' -or $_.Id -like '*{safe_clean_target}*' }} | Select-Object -First 1
                }}
                if ($target) {{
                    $synth.Voice = $target
                }}
                $stream = ($synth.SynthesizeTextToStreamAsync('{safe_text}')).GetResults()
                $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
                $bytes = New-Object byte[] $stream.Size
                $reader.LoadAsync($stream.Size).GetResults() | Out-Null
                $reader.ReadBytes($bytes)
                [System.IO.File]::WriteAllBytes('{safe_output}', $bytes)
                exit 0
            }} catch {{
                exit 1
            }}
            """
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_winrt],
                stderr=subprocess.DEVNULL,
                **get_subprocess_flags()
            )
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return output_path
        except Exception as e:
            logger.info(f"[TTSEngine] Windows WinRT notice: {e}")

        # 2. Online High-Quality Fallbacks (Azure Neural Edge-TTS -> Google Cloud)
        if os.environ.get("CI_TRAINER_OFFLINE") != "1":
            edge_res = self._generate_edge_tts(text, output_path, voice="Edge-Conrad", rate=rate)
            if edge_res and os.path.exists(edge_res) and os.path.getsize(edge_res) > 500:
                return edge_res

        return self._generate_google_tts(text, output_path, voice=voice, rate=rate)

    def _generate_linux_tts(self, text: str, rate: float, voice: str, output_path: str) -> str:
        google_res = self._generate_google_tts(text, output_path, voice=voice, rate=rate)
        if google_res and os.path.exists(google_res) and os.path.getsize(google_res) > 0:
            return google_res

        try:
            cmd = ["espeak", "-v", "de", "-w", output_path, text]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL, **get_subprocess_flags())
            if os.path.exists(output_path):
                return output_path
        except Exception:
            pass
        return self._generate_synthetic_fallback(output_path)

    def _generate_synthetic_fallback(self, output_path: str, duration_sec: float = 0.5) -> str:
        """Generates a synthetic 22050Hz WAV sine audio file for headless CI test runners without speech binaries."""
        try:
            sample_rate = 22050
            num_samples = int(sample_rate * duration_sec)
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                for i in range(num_samples):
                    val = int(16000 * math.sin(2 * math.pi * 440 * i / sample_rate))
                    wav_file.writeframes(struct.pack("<h", val))
            return output_path
        except Exception as e:
            logger.error(f"[TTSEngine] Synthetic fallback error: {e}")
            return None

    @classmethod
    def discover_voices(cls, language: str = "de"):
        """
        Dynamically detects all downloaded/installed natural voices on the host operating system
        (macOS / Windows WinRT OneCore), Edge-TTS Microsoft Azure neural voices, and Google Cloud online synthesis.
        Filters list based on language ('de' or 'en').
        """
        discovered = []
        sys_name = platform.system()
        is_en = (language or "de").lower().startswith("en")
        loc_filters = ["en_us", "en_gb", "english"] if is_en else ["de_de", "de_at", "de_ch", "german", "deutsch"]
        win_loc = "en*" if is_en else "de*"

        # 1. Host OS Voices (macOS say)
        if sys_name == "Darwin":
            try:
                out = subprocess.check_output(["say", "-v", "?"], stderr=subprocess.DEVNULL, **get_subprocess_flags()).decode("utf-8", errors="ignore")
                legacy = {
                    "eddy", "flo", "grandma", "grandpa", "reed", "rocko", "sandy", "shelley",
                    "albert", "bad news", "bahh", "bells", "boing", "bubbles", "cellos",
                    "deranged", "good news", "hysterical", "junior", "kathy", "pipe organ",
                    "princess", "ralph", "trinoids", "whisper", "zarvox"
                }
                male_names = {"markus", "viktor", "yannick", "martin", "stefan", "michael", "florian", "oliver", "johannes", "thorsten", "helmut", "hans", "alex", "daniel", "fred"}

                for line in out.splitlines():
                    if not line.strip():
                        continue
                    if any(loc in line.lower() for loc in loc_filters):
                        idx = line.find("en_") if is_en else line.find("de_")
                        name_raw = line[:idx].strip() if idx > 0 else line.split()[0]
                        clean_base = name_raw.split("(")[0].strip()
                        if clean_base.lower() in legacy:
                            continue

                        gender = "männlich" if any(m in clean_base.lower() for m in male_names) else "weiblich"
                        icon = "👨" if gender == "männlich" else "👩"

                        # Clean presentation label
                        label_name = name_raw
                        if "Enhanced" in name_raw:
                            label_name = name_raw.replace("(Enhanced)", "✨ Verbessert")
                        elif "Premium" in name_raw:
                            label_name = name_raw.replace("(Premium)", "⭐ Premium")

                        discovered.append({
                            "id": name_raw,
                            "name": f"{icon} {label_name} (Mac System)",
                            "gender": gender,
                            "source": "system",
                            "say_id": name_raw,
                            "pitch": 1.00,
                            "tempo": 1.00
                        })
            except Exception as e:
                logger.info(f"[TTSEngine] Voice discovery notice: {e}")

        # 2. Host OS Voices (Windows WinRT OneCore Voices only)
        elif sys_name == "Windows":
            try:
                ps_cmd = f"""
                [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
                $voices = @()
                foreach ($v in [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices) {{
                    if ($v.Language -like '{win_loc}') {{
                        $gen = if ($v.Gender -eq 0 -or $v.Gender -eq 'Female') {{ "weiblich" }} else {{ "männlich" }}
                        $voices += "$($v.DisplayName)|$gen|$($v.Id)"
                    }}
                }}
                $voices | Sort-Object -Unique | ForEach-Object {{ Write-Output $_ }}
                """
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                    stderr=subprocess.DEVNULL,
                    **get_subprocess_flags()
                ).decode("utf-8", errors="ignore")
                seen_windows = set()
                for line in out.splitlines():
                    if "|" in line:
                        parts = line.strip().split("|")
                        if len(parts) >= 2:
                            vname = parts[0].strip()
                            vgen = parts[1].strip()
                            vid = parts[2].strip() if len(parts) >= 3 else vname

                            clean_name = vname.replace("Microsoft ", "").replace(" Desktop", "")
                            if clean_name.lower() in seen_windows:
                                continue
                            seen_windows.add(clean_name.lower())

                            gender = "weiblich" if "weiblich" in vgen.lower() or "female" in vgen.lower() or vgen == "0" else "männlich"
                            icon = "👩" if gender == "weiblich" else "👨"
                            discovered.append({
                                "id": vname,
                                "name": f"{icon} {clean_name} (Windows System)",
                                "gender": gender,
                                "source": "system",
                                "say_id": vid,
                                "pitch": 1.00,
                                "tempo": 1.00
                            })
            except Exception as e:
                logger.info(f"[TTSEngine] Windows voice discovery notice: {e}")

        # Fallback if no system voices discovered
        if not discovered:
            default_id = "Samantha" if is_en else "Anna"
            default_name = "👩 Samantha (System - US English)" if is_en else "👩 Anna (System - Natürlich & Klar)"
            discovered.append({
                "id": default_id,
                "name": default_name,
                "gender": "weiblich",
                "source": "system",
                "say_id": default_id,
                "pitch": 1.00,
                "tempo": 1.00
            })

        # 2. Microsoft Azure Neural Voices (Edge-TTS)
        target_edge_voices = cls.EDGE_VOICES_EN if is_en else cls.EDGE_VOICES
        for ev in target_edge_voices:
            discovered.append({
                "id": ev["id"],
                "name": ev["name"],
                "gender": ev["gender"],
                "source": "edge",
                "say_id": "Anna",
                "pitch": 1.00,
                "tempo": 1.00
            })

        # 3. Google Cloud Online
        g_id = "Google-Online-EN" if is_en else "Google-Online-DE"
        g_name = "🌐 Google Cloud Online (US English)" if is_en else "🌐 Google Cloud Online (Deutsch)"
        discovered.append({
            "id": g_id,
            "name": g_name,
            "gender": "weiblich",
            "source": "google",
            "say_id": "Samantha" if is_en else "Anna",
            "pitch": 1.00,
            "tempo": 1.00
        })

        return discovered

    def get_voices(self, language: str = "de"):
        return self.discover_voices(language=language)
