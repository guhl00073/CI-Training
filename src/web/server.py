import http.server
import socketserver
import json
import urllib.parse
import os
import pathlib
import threading
import webbrowser
import uuid
import sys
import time
import signal
import atexit

from src.audio.tts_engine import TTSEngine
from src.audio.player import AudioPlayer
from src.evaluator.phonetic_matcher import PhoneticMatcher
from src.database.progress_db import ProgressDatabase
from src.audio.olsa_adaptive import AdaptiveOLSA
from src.audio.ci_vocoder import CIVocoder
from src.stt.stt_engine import STTEngine
from src.utils.paths import get_resource_path, get_subprocess_flags
from src.utils.logger import get_logger

logger = get_logger(__name__)

PORT = 8080
STATIC_DIR = get_resource_path("src/web/static")

# Valid module types accepted by the exercise CRUD endpoints
VALID_MOD_TYPES = {"minimal_pairs", "monosyllables", "multisyllables", "words", "numbers", "sentences"}


def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_bool(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


class CITrainerHTTPHandler(http.server.SimpleHTTPRequestHandler):
    tts = TTSEngine()
    player = AudioPlayer()
    matcher = PhoneticMatcher()
    db = ProgressDatabase()
    olsa_session = AdaptiveOLSA()
    vocoder = CIVocoder()
    stt = STTEngine()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # ─── GET ──────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/exercises":
            # Serve all exercises from the SQLite database (filtered by active language)
            lang = params.get("lang", ["de"])[0]
            self._send_json(self.db.get_all_exercises(lang=lang))

        elif path == "/api/exercises/weaknesses":
            self._send_json(self.db.get_weak_exercises())

        elif path == "/api/voices":
            lang = params.get("lang", ["de"])[0]
            self._send_json(self.tts.get_voices(language=lang))

        elif path == "/api/stats":
            self._send_json(self.db.get_summary_stats())

        elif path == "/api/logs":
            limit = int(params.get("limit", [100])[0]) if "limit" in params else 100
            offset = int(params.get("offset", [0])[0]) if "offset" in params else 0
            module = params.get("module", [None])[0] if "module" in params else None
            filter_status = params.get("status", [None])[0] if "status" in params else None
            self._send_json(self.db.get_training_logs(limit=limit, offset=offset, module=module, filter_status=filter_status))

        elif path == "/api/system_logs":
            try:
                from src.utils.paths import get_user_data_dir
                log_file = get_user_data_dir() / "logs" / "ci_training.log"
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        self._send_json({"logs": "".join(lines[-1000:])})
                else:
                    self._send_json({"logs": "Logdatei nicht gefunden."})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif path in ("/api/test_lists", "/api/test_lists/words"):
            self._send_json(self.db.get_freiburger_test_lists())

        elif path == "/api/test_lists/numbers":
            self._send_json(self.db.get_freiburger_number_lists())

        elif path == "/api/test_runs":
            self._send_json(self.db.get_test_runs())

        elif path == "/api/olsa/runs":
            self._send_json(self.db.get_olsa_runs())

        elif path == "/api/freiburger/curves":
            self._send_json(self.db.get_freiburger_curves())

        elif path == "/api/reports/therapist":
            self._send_json(self.db.get_therapist_report())


        elif path == "/api/profiles":
            self._send_json(self.db.get_profiles())

        elif path == "/api/profiles/active":
            self._send_json(self.db.get_active_profile())

        elif path == "/api/shutdown":
            self._send_json({"status": "shutting_down", "message": "Server wird heruntergefahren."})
            def _shutdown():
                time.sleep(0.3)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()

        elif path.startswith("/api/audio/"):
            # Serve temporary TTS audio files from the cache dir
            file_name = os.path.basename(path)
            cache_dir = pathlib.Path(self.tts.cache_dir)
            target_path = cache_dir / file_name
            if target_path.exists() and target_path.is_file():
                self._send_file(str(target_path), "audio/wav")
            else:
                self.send_error(404, "Audio file not found")

        else:
            super().do_GET()

    # ─── OPTIONS (CORS pre-flight) ────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._add_cors_headers()
        self.end_headers()

    # ─── POST ─────────────────────────────────────────────────────────────────

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/shutdown":
            self._send_json({"status": "shutting_down", "message": "Server wird heruntergefahren."})
            def _shutdown():
                try:
                    CITrainerHTTPHandler.player.stop()
                except Exception as _e:
                    logger.error(f"[Server] Cleanup: player.stop() failed: {_e}")
                time.sleep(0.2)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()
            return

        elif path == "/api/upload_image":
            raw_filename = body.get("filename", "image.png")
            safe_filename = pathlib.Path(raw_filename).name
            if not safe_filename:
                safe_filename = "image.png"
            data_url = body.get("data", "")
            if "," in data_url:
                data_url = data_url.split(",", 1)[1]
            import base64
            try:
                img_bytes = base64.b64decode(data_url)
            except Exception as e:
                logger.error(f"[Server] /api/upload_image base64 decode error: {e}")
                self._send_error(400, "Invalid image base64 data.")
                return
            save_dir = (pathlib.Path(__file__).parent.parent.parent / "docs" / "images").resolve()
            save_dir.mkdir(parents=True, exist_ok=True)
            out_file = (save_dir / safe_filename).resolve()
            if not str(out_file).startswith(str(save_dir)):
                self._send_error(400, "Invalid image path.")
                return
            with open(out_file, "wb") as f:
                f.write(img_bytes)
            self._send_json({"status": "saved", "file": str(out_file)})
            return

        elif path == "/api/tts":
            text = body.get("text", "") or ""
            rate = safe_float(body.get("rate"), 1.0)
            balance = safe_float(body.get("balance"), 0.0)
            volume = safe_float(body.get("volume"), 1.0)
            voice = body.get("voice") or "Anna"
            mask_noise = safe_bool(body.get("mask_noise"), True)
            noise_volume = safe_float(body.get("noise_volume"), 0.4)
            ambient_noise = safe_bool(body.get("ambient_noise"), False)
            ambient_type = str(body.get("ambient_type") or "noise")
            ambient_volume = safe_float(body.get("ambient_volume"), 0.3)
            freq_filter = str(body.get("freq_filter") or "none")
            wait = safe_bool(body.get("wait"), False)

            audio_file = self.tts.generate_audio(text, rate=rate, voice=voice)
            vocoder_enabled = safe_bool(body.get("vocoder_enabled"), False)
            if vocoder_enabled:
                profile_key = str(body.get("vocoder_profile") or "ab_16")
                profile = self.vocoder.PROFILES.get(profile_key, {"channels": 16, "carrier": "sine"})
                carrier = str(body.get("vocoder_carrier") or profile.get("carrier", "sine"))
                channels = int(profile.get("channels", 16))
                vocoded_name = f"vocoded_{uuid.uuid4().hex[:8]}.wav"
                cache_dir = pathlib.Path(self.tts.cache_dir)
                vocoded_path = cache_dir / vocoded_name
                if self.vocoder.process_wav(audio_file, str(vocoded_path), num_channels=channels, carrier_type="sine"):
                    audio_file = str(vocoded_path)

            self.player.play(
                audio_file, balance=balance, volume=volume, rate=rate,
                mask_noise=mask_noise, noise_volume=noise_volume,
                ambient_noise=ambient_noise, ambient_type=ambient_type,
                ambient_volume=ambient_volume, freq_filter=freq_filter, wait_until_done=wait,
            )
            file_name = os.path.basename(audio_file)
            self._send_json({"status": "playing", "file": file_name, "text": text, "voice": voice, "vocoded": vocoder_enabled})

        elif path == "/api/noise/config":
            self.player.sync_noise(
                mask_noise=safe_bool(body.get("mask_noise"), True),
                ambient_noise=safe_bool(body.get("ambient_noise"), False),
                ambient_type=str(body.get("ambient_type") or "noise"),
                balance=safe_float(body.get("balance"), 0.0),
                noise_volume=safe_float(body.get("noise_volume"), 0.4),
                ambient_volume=safe_float(body.get("ambient_volume"), 0.3),
            )
            self._send_json({"status": "synced"})

        elif path == "/api/noise/stop":
            self.player.stop_noise()
            self._send_json({"status": "stopped"})

        elif path == "/api/audio/stop":
            self.player.stop()
            self._send_json({"status": "stopped"})

        elif path == "/api/calibration/start":
            signal_type = str(body.get("signal_type") or "speech_noise")
            volume = safe_float(body.get("volume"), 0.5)
            self.player.start_calibration(signal_type=signal_type, volume=volume)
            self._send_json({"status": "started", "signal_type": signal_type})

        elif path == "/api/calibration/stop":
            self.player.stop_calibration()
            self._send_json({"status": "stopped"})


        elif path == "/api/evaluate":
            target = body.get("target", "")
            user_input = body.get("user_input", "")
            spoken = body.get("spoken", target)
            module = body.get("module", "General")
            category = body.get("category", "")
            lang = body.get("lang") or body.get("language") or "de"

            if module == "Zahlen":
                eval_res = self.matcher.evaluate_number(target, spoken, user_input)
            elif module == "Sentences_Full":
                eval_res = self.matcher.evaluate_full_sentence(target, user_input)
            else:
                eval_res = self.matcher.evaluate(target, user_input, language=lang)

            self.db.log_attempt(
                module=module,
                category=eval_res.get("phonetic_category") or category,
                target_word=target,
                user_answer=user_input,
                is_correct=eval_res["is_correct"],
                score=eval_res["score"],
            )
            self._send_json(eval_res)

        elif path == "/api/stats/reset":
            self.db.reset_stats()
            self._send_json({"status": "reset", "stats": self.db.get_summary_stats()})

        elif path == "/api/logs/delete":
            log_id = body.get("id")
            if log_id is None:
                self._send_error(400, "Missing log ID.")
                return
            success = self.db.delete_training_log(int(log_id))
            self._send_json({"success": success, "message": "Protokolleintrag gelöscht." if success else "Eintrag nicht gefunden."})

        elif path == "/api/test_run/log":
            list_name = body.get("list_name", body.get("test_name", "Freiburger Einsilbertest (DIN 45621)"))
            total_words = int(body.get("total_words", 20))
            correct_words = int(body.get("correct_words", 0))
            score = float(body.get("score", body.get("score_percent", 0.0)))
            details_json = body.get("details_json", None)
            self.db.log_test_run(list_name, total_words, correct_words, score, details_json)
            self._send_json({"status": "logged", "message": "Testlauf erfolgreich protokolliert."})
        elif path == "/api/exercises":
            # ── CREATE a new exercise ─────────────────────────────────────────
            mod_type = body.get("mod_type", "")
            item = body.get("item", {})
            if mod_type not in VALID_MOD_TYPES or not isinstance(item, dict):
                self._send_error(400, "Invalid mod_type or item payload.")
                return
            try:
                created = self.db.add_exercise(mod_type, item)
                self._send_json({"status": "created", "item": created, "message": "✅ Übung erfolgreich gespeichert!"})
            except Exception as e:
                logger.error(f"[Server] /api/exercises POST error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/exercises/bulk":
            # ── BULK CREATE exercises ─────────────────────────────────────────
            mod_type = body.get("mod_type", "")
            items = body.get("items", [])
            if mod_type not in VALID_MOD_TYPES or not isinstance(items, list):
                self._send_error(400, "Invalid mod_type or items array.")
                return
            try:
                created_list = self.db.bulk_add_exercises(mod_type, items)
                self._send_json({
                    "status": "bulk_created",
                    "count": len(created_list),
                    "items": created_list,
                    "message": f"✅ {len(created_list)} Übungen erfolgreich importiert!"
                })
            except Exception as e:
                logger.error(f"[Server] /api/exercises/bulk POST error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/categories/rename":
            mod_type = body.get("mod_type", "")
            old_cat = body.get("old_category", "").strip()
            new_cat = body.get("new_category", "").strip()
            if mod_type not in VALID_MOD_TYPES or not old_cat or not new_cat:
                self._send_error(400, "Missing or invalid mod_type, old_category or new_category.")
                return
            try:
                count = self.db.rename_category(mod_type, old_cat, new_cat)
                self._send_json({
                    "status": "renamed",
                    "count": count,
                    "message": f"✅ Kategorie '{old_cat}' in '{new_cat}' umbenannt ({count} Einträge aktualisiert)."
                })
            except Exception as e:
                logger.error(f"[Server] /api/categories/rename error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/categories/delete":
            mod_type = body.get("mod_type", "")
            cat = body.get("category", "").strip()
            only_custom = safe_bool(body.get("only_custom", True), True)
            if mod_type not in VALID_MOD_TYPES or not cat:
                self._send_error(400, "Missing mod_type or category.")
                return
            try:
                count = self.db.delete_category(mod_type, cat, only_custom=only_custom)
                self._send_json({
                    "status": "deleted",
                    "count": count,
                    "message": f"🗑️ {count} Übungen der Kategorie '{cat}' gelöscht."
                })
            except Exception as e:
                logger.error(f"[Server] /api/categories/delete error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/olsa/start":
            start_snr = safe_float(body.get("start_snr_db"), 0.0)
            noise_type = str(body.get("noise_type") or "olnoise")
            total_sent = int(body.get("total_sentences") or 20)
            CITrainerHTTPHandler.olsa_session = AdaptiveOLSA(initial_snr_db=start_snr, noise_type=noise_type, total_sentences=total_sent)
            session_data = CITrainerHTTPHandler.olsa_session.start_new_test(start_snr_db=start_snr)

            # Synthesize sentence speech and mix with noise
            target_sent = session_data["target_sentence"]
            voice = str(body.get("voice") or "Anna")
            speech_wav = self.tts.generate_audio(target_sent, rate=1.0, voice=voice)
            
            cache_dir = pathlib.Path(self.tts.cache_dir)
            mixed_wav_name = f"olsa_mixed_{uuid.uuid4().hex[:8]}.wav"
            mixed_wav_path = cache_dir / mixed_wav_name
            AdaptiveOLSA.mix_speech_with_noise(speech_wav, str(mixed_wav_path), snr_db=start_snr, noise_type=noise_type)

            # Play via system audio player
            self.player.play(str(mixed_wav_path), mask_noise=False)

            session_data["audio_file"] = mixed_wav_name
            session_data["speech_file"] = os.path.basename(speech_wav)
            self._send_json(session_data)

        elif path == "/api/olsa/play":
            file_name = str(body.get("audio_file") or "")
            cache_dir = pathlib.Path(self.tts.cache_dir)
            target_path = cache_dir / os.path.basename(file_name)
            if target_path.exists() and target_path.is_file():
                self.player.play(str(target_path), mask_noise=False)
                self._send_json({"status": "playing", "file": file_name})
            else:
                self._send_error(404, "Audio file not found.")

        elif path == "/api/olsa/step":
            selected_words = body.get("selected_words", [])
            voice = str(body.get("voice") or "Anna")
            noise_type = CITrainerHTTPHandler.olsa_session.noise_type
            result = CITrainerHTTPHandler.olsa_session.process_response(selected_words)

            if result.get("finished"):
                # Save completed run to DB
                self.db.log_olsa_run(
                    srt_db=result["srt_db"],
                    initial_snr=CITrainerHTTPHandler.olsa_session.history[0]["snr_db"] if CITrainerHTTPHandler.olsa_session.history else 0.0,
                    noise_type=noise_type,
                    total_sentences=CITrainerHTTPHandler.olsa_session.total_sentences,
                    std_dev=result["std_dev"],
                    history=result["history"]
                )
            else:
                next_sent = result["next_target_sentence"]
                next_snr = result["next_snr_db"]
                speech_wav = self.tts.generate_audio(next_sent, rate=1.0, voice=voice)
                cache_dir = pathlib.Path(self.tts.cache_dir)
                mixed_wav_name = f"olsa_mixed_{uuid.uuid4().hex[:8]}.wav"
                mixed_wav_path = cache_dir / mixed_wav_name
                AdaptiveOLSA.mix_speech_with_noise(speech_wav, str(mixed_wav_path), snr_db=next_snr, noise_type=noise_type)
                
                # Play via system audio player
                self.player.play(str(mixed_wav_path), mask_noise=False)
                result["audio_file"] = mixed_wav_name

            self._send_json(result)

        elif path == "/api/freiburger/curve":
            list_name = str(body.get("list_name") or "Liste 1")
            test_data = body.get("test_data", [])
            v_max = safe_float(body.get("v_max"), 0.0)
            disc_loss = safe_float(body.get("disc_loss"), 0.0)
            notes = str(body.get("notes") or "")
            curve_id = self.db.log_freiburger_curve(list_name, test_data, v_max, disc_loss, notes)
            self._send_json({"status": "saved", "curve_id": curve_id})


        elif path == "/api/profiles":
            profile = self.db.create_profile(body)
            self._send_json({"status": "created", "profile": profile})

        elif path == "/api/profiles/activate" or (path.startswith("/api/profiles/") and path.endswith("/activate")):
            profile_id = body.get("id") or path.split("/")[3]
            success = self.db.set_active_profile(profile_id)
            if success:
                active_p = self.db.get_active_profile()
                self._send_json({"status": "activated", "active_profile": active_p})
            else:
                self._send_error(404, f"Profile '{profile_id}' not found.")

        else:
            self.send_error(404, "Endpoint not found")

    # ─── PUT ──────────────────────────────────────────────────────────────────

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/exercises":
            # ── UPDATE an existing exercise ──────────────────────────────────
            mod_type = body.get("mod_type", "")
            item = body.get("item", {})
            if mod_type not in VALID_MOD_TYPES or not isinstance(item, dict) or not item.get("id"):
                self._send_error(400, "Invalid mod_type, item payload, or missing id.")
                return
            try:
                updated = self.db.update_exercise(mod_type, item)
                if updated:
                    self._send_json({"status": "updated", "item": item})
                else:
                    self._send_error(404, f"Exercise '{item.get('id')}' not found.")
            except Exception as e:
                logger.error(f"[Server] /api/exercises PUT error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/profiles" or path.startswith("/api/profiles/"):
            parts = path.strip("/").split("/")
            profile_id = parts[2] if len(parts) >= 3 else body.get("id", "")
            if not profile_id:
                self._send_error(400, "Missing profile_id.")
                return
            updated = self.db.update_profile(profile_id, body)
            if updated:
                self._send_json({"status": "updated", "profile": updated})
            else:
                self._send_error(404, f"Profile '{profile_id}' not found.")

        else:
            self.send_error(404, "Endpoint not found")

    # ─── DELETE ───────────────────────────────────────────────────────────────

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        if path == "/api/exercises":
            # ── DELETE an exercise ───────────────────────────────────────────
            mod_type = body.get("mod_type", "")
            item_id = body.get("item_id", "")
            if mod_type not in VALID_MOD_TYPES or not item_id:
                self._send_error(400, "Invalid mod_type or missing item_id.")
                return
            try:
                deleted = self.db.delete_exercise(mod_type, item_id)
                if deleted:
                    self._send_json({"status": "deleted", "item_id": item_id})
                else:
                    self._send_error(404, f"Exercise '{item_id}' not found.")
            except Exception as e:
                logger.error(f"[Server] /api/exercises DELETE error: {e}")
                self._send_error(500, str(e))

        elif path == "/api/profiles" or path.startswith("/api/profiles/"):
            parts = path.strip("/").split("/")
            profile_id = parts[2] if len(parts) >= 3 else body.get("id", "")
            if not profile_id:
                self._send_error(400, "Missing profile_id.")
                return
            success = self.db.delete_profile(profile_id)
            if success:
                self._send_json({"status": "deleted", "profile_id": profile_id, "profiles": self.db.get_profiles()})
            else:
                self._send_error(400, f"Cannot delete profile '{profile_id}' (must have at least one profile).")

        else:
            self.send_error(404, "Endpoint not found")

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.error(f"[Server] _read_body JSON parse error: {e}")
            return {}

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, data, status: int = 200):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, status: int, message: str):
        self._send_json({"error": message}, status=status)

    def _send_file(self, file_path, content_type):
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        # Suppress default per-request logging noise; errors still surface
        pass


# ─── SERVER LIFECYCLE ─────────────────────────────────────────────────────────

def free_port(port: int):
    """Terminates any process currently bound to the specified port so it can be cleanly reused."""
    import platform
    import subprocess
    import signal
    import time

    current_pid = os.getpid()

    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                f"netstat -ano | findstr :{port}", shell=True, **get_subprocess_flags()
            ).decode(errors="ignore")
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1]:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid != current_pid and pid > 0:
                            subprocess.run(
                                f"taskkill /F /PID {pid}", shell=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                **get_subprocess_flags()
                            )
        except subprocess.CalledProcessError:
            pass  # Expected if no process is using the port
        except Exception as e:
            logger.error(f"[Server] free_port (Windows) error: {e}")
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            for pid_str in out.strip().splitlines():
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != current_pid and pid > 0:
                        try:
                            # Resume if suspended (^Z) before terminating
                            os.kill(pid, signal.SIGCONT)
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(0.1)
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
        except subprocess.CalledProcessError:
            pass  # Expected if no process is using the port
        except Exception as e:
            logger.error(f"[Server] free_port (Unix) error: {e}")
    time.sleep(0.2)


class QuietTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        exctype, val, tb = sys.exc_info()
        if exctype in (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            return
        super().handle_error(request, client_address)


def start_web_server(open_browser: bool = True):
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    port = PORT
    free_port(port)

    httpd = None
    try:
        httpd = QuietTCPServer(("", port), CITrainerHTTPHandler)
    except OSError:
        free_port(port)
        try:
            httpd = QuietTCPServer(("", port), CITrainerHTTPHandler)
        except OSError as e:
            logger.error(f"❌ Fehler: Port {port} konnte nicht freigegeben werden ({e}).")
            return

    def _cleanup(*args):
        try:
            CITrainerHTTPHandler.player.stop()
        except Exception as e:
            logger.error(f"[Server] Cleanup player.stop() error: {e}")
        if httpd:
            try:
                httpd.server_close()
            except Exception as e:
                logger.error(f"[Server] server_close() error: {e}")

    def _sig_handler(signum, frame):
        if signum in (signal.SIGINT, signal.SIGTERM):
            _cleanup()
            sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
    except Exception as e:
        # Signal registration may fail on Windows – non-critical
        logger.info(f"[Server] Signal-Handler Registrierung: {e}")
    atexit.register(_cleanup)

    url = f"http://localhost:{port}"
    logger.info(f"🚀 CI-Hörtrainer Modern Web UI gestartet unter {url}")
    if open_browser:
        def _launch_browser():
            if sys.platform == "darwin":
                try:
                    import subprocess
                    subprocess.Popen(["open", url])
                    return
                except Exception as e:
                    logger.error(f"[Server] open browser subprocess error: {e}")
            webbrowser.open(url)

        threading.Timer(0.8, _launch_browser).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer wird beendet.")
    finally:
        _cleanup()

