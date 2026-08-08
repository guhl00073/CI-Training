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

from src.audio.tts_engine import TTSEngine
from src.audio.player import AudioPlayer
from src.evaluator.phonetic_matcher import PhoneticMatcher
from src.database.progress_db import ProgressDatabase

PORT = 8080
STATIC_DIR = pathlib.Path(__file__).parent / "static"

# Valid module types accepted by the exercise CRUD endpoints
VALID_MOD_TYPES = {"minimal_pairs", "monosyllables", "numbers", "sentences"}


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
    player = AudioPlayer(noise_file="data/rauschen.mp3")
    matcher = PhoneticMatcher()
    db = ProgressDatabase()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # ─── GET ──────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/exercises":
            # Serve all exercises from the SQLite database (backwards-compatible format)
            self._send_json(self.db.get_all_exercises())

        elif path == "/api/voices":
            self._send_json(self.tts.get_voices())

        elif path == "/api/stats":
            self._send_json(self.db.get_summary_stats())

        elif path.startswith("/api/audio/"):
            # Serve temporary TTS audio files from the system temp dir
            file_name = os.path.basename(path)
            temp_dir = pathlib.Path(self.tts.temp_dir)
            target_path = temp_dir / file_name
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

        if path == "/api/tts":
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
            wait = safe_bool(body.get("wait"), False)

            audio_file = self.tts.generate_audio(text, rate=rate, voice=voice)
            self.player.play(
                audio_file, balance=balance, volume=volume, rate=rate,
                mask_noise=mask_noise, noise_volume=noise_volume,
                ambient_noise=ambient_noise, ambient_type=ambient_type,
                ambient_volume=ambient_volume, wait_until_done=wait,
            )
            file_name = os.path.basename(audio_file)
            self._send_json({"status": "playing", "file": file_name, "text": text, "voice": voice})

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

        elif path == "/api/evaluate":
            target = body.get("target", "")
            user_input = body.get("user_input", "")
            spoken = body.get("spoken", target)
            module = body.get("module", "General")
            category = body.get("category", "")

            if module == "Zahlen":
                eval_res = self.matcher.evaluate_number(target, spoken, user_input)
            else:
                eval_res = self.matcher.evaluate(target, user_input)

            self.db.log_attempt(
                module=module,
                category=category,
                target_word=target,
                user_answer=user_input,
                is_correct=eval_res["is_correct"],
                score=eval_res["score"],
            )
            self._send_json(eval_res)

        elif path == "/api/stats/reset":
            self.db.reset_stats()
            self._send_json({"status": "reset", "stats": self.db.get_summary_stats()})

        elif path == "/api/exercises":
            # ── CREATE a new exercise ────────────────────────────────────────
            mod_type = body.get("mod_type", "")
            item = body.get("item", {})
            if mod_type not in VALID_MOD_TYPES or not isinstance(item, dict):
                self._send_error(400, "Invalid mod_type or item payload.")
                return
            try:
                created = self.db.add_exercise(mod_type, item)
                self._send_json({"status": "created", "item": created}, status=201)
            except Exception as e:
                self._send_error(500, str(e))

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
                self._send_error(500, str(e))

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
                self._send_error(500, str(e))

        else:
            self.send_error(404, "Endpoint not found")

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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
                f"netstat -ano | findstr :{port}", shell=True
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
                            )
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"]
            ).decode(errors="ignore")
            for pid_str in out.strip().splitlines():
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != current_pid and pid > 0:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
        except Exception:
            pass
    time.sleep(0.2)


def start_web_server(open_browser: bool = True):
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    socketserver.TCPServer.allow_reuse_address = True

    port = PORT
    free_port(port)

    httpd = None
    try:
        httpd = socketserver.TCPServer(("", port), CITrainerHTTPHandler)
    except OSError:
        free_port(port)
        try:
            httpd = socketserver.TCPServer(("", port), CITrainerHTTPHandler)
        except OSError as e:
            print(f"❌ Fehler: Port {port} konnte nicht freigegeben werden ({e}).")
            return

    url = f"http://localhost:{port}"
    print(f"🚀 CI-Hörtrainer Modern Web UI gestartet unter {url}")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer wird beendet.")
        httpd.server_close()
