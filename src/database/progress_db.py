import sqlite3
import pathlib
import json
import os
import uuid
import threading
from datetime import datetime

from src.utils.paths import get_resource_path, get_db_path
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressDatabase:
    """
    SQLite Database Manager for tracking CI hearing training progress,
    statistics, and exercise catalog (Minimal pairs, Monosyllables, Numbers, Sentences).
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = str(get_db_path())
        else:
            self.db_path = str(db_path)
        self._lock = threading.RLock()
        if self.db_path != ":memory:":
            pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        if self.db_path != ":memory:":
            try:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
        self._init_db()
        self._seed_if_empty()

    def _get_connection(self):
        return self.conn

    # ─── SCHEMA INITIALISATION ─────────────────────────────────────────────────

    def _init_db(self):
        """Creates all tables if they do not yet exist."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Training Logs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS training_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        module TEXT NOT NULL,
                        category TEXT,
                        target_word TEXT NOT NULL,
                        user_answer TEXT,
                        is_correct INTEGER NOT NULL,
                        score REAL NOT NULL,
                        snr_db REAL DEFAULT 0.0
                    )
                """)

                # 2. Exercises: Minimal Pairs
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercises_minimal_pairs (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        source TEXT NOT NULL,
                        options_json TEXT,
                        word_a TEXT,
                        word_b TEXT,
                        difficulty TEXT DEFAULT 'Mittel',
                        hint TEXT
                    )
                """)

                # 3. Exercises: Words (Monosyllables, Multisyllables, Compound Words)
                # Auto-migrate legacy table name exercises_monosyllables -> exercises_words
                try:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises_monosyllables'")
                    if cursor.fetchone():
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises_words'")
                        if not cursor.fetchone():
                            cursor.execute("ALTER TABLE exercises_monosyllables RENAME TO exercises_words")
                except Exception:
                    pass

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercises_words (
                        id TEXT PRIMARY KEY,
                        word TEXT NOT NULL,
                        category TEXT DEFAULT 'Einsilber',
                        source TEXT DEFAULT 'Freiburger Einsilber-Test (DIN 45621)',
                        difficulty TEXT DEFAULT 'Einfach',
                        list_num INTEGER DEFAULT 1,
                        syllables TEXT,
                        syllable_count INTEGER DEFAULT 1,
                        stress TEXT,
                        hint TEXT
                    )
                """)

                # 4. Exercises: Numbers / Times / Amounts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercises_numbers (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        value TEXT NOT NULL,
                        spoken TEXT NOT NULL,
                        difficulty TEXT DEFAULT 'Einfach'
                    )
                """)

                # 5. Exercises: Sentences (OLSA)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exercises_sentences (
                        id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        source TEXT NOT NULL,
                        sentence TEXT NOT NULL,
                        target_word TEXT NOT NULL,
                        options_json TEXT NOT NULL,
                        hint TEXT
                    )
                """)

                # 6. Structured Clinical Test Runs (Freiburger Testlisten DIN 45621)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        list_name TEXT NOT NULL,
                        total_words INTEGER NOT NULL,
                        correct_words INTEGER NOT NULL,
                        score REAL NOT NULL,
                        details_json TEXT
                    )
                """)

                # 7. Adaptive OLSA Speech Audiometry Runs (Brand & Kollmeier SRT)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS olsa_test_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        srt_db REAL NOT NULL,
                        initial_snr REAL NOT NULL,
                        noise_type TEXT NOT NULL,
                        total_sentences INTEGER NOT NULL,
                        std_dev REAL DEFAULT 0.0,
                        history_json TEXT
                    )
                """)

                # 8. Freiburger Multi-Level Sprachaudiometrie Curves (DIN 45621)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS freiburger_audiograms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        list_name TEXT NOT NULL,
                        test_data_json TEXT NOT NULL,
                        v_max REAL NOT NULL,
                        disc_loss REAL NOT NULL,
                        notes TEXT
                    )
                """)

                # 9. Multi-User & CI-Specific User Profiles
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        fitting_type TEXT NOT NULL DEFAULT 'bilateral',
                        implant_model TEXT DEFAULT 'Cochlear Nucleus 8',
                        first_fitting_date TEXT,
                        audio_balance REAL DEFAULT 0.0,
                        master_gain REAL DEFAULT 1.0,
                        speech_rate REAL DEFAULT 1.0,
                        voice TEXT DEFAULT 'Anna',
                        voice_en TEXT DEFAULT 'Edge-EN-Ava',
                        exercise_lang TEXT DEFAULT 'de',
                        mask_noise INTEGER DEFAULT 0,
                        noise_volume REAL DEFAULT 0.4,
                        freq_filter TEXT DEFAULT 'none',
                        autostart_success_delay REAL DEFAULT 1.8,
                        autostart_error_delay REAL DEFAULT 5.0,
                        auto_mic INTEGER DEFAULT 1,
                        auto_start INTEGER DEFAULT 0,
                        adaptive_snr INTEGER DEFAULT 0,
                        vocoder_enabled INTEGER DEFAULT 0,
                        vocoder_profile TEXT DEFAULT 'medel_12',
                        is_active INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Automatic migration of extra settings columns
                for col_name, col_def in [
                    ("freq_filter", "TEXT DEFAULT 'none'"),
                    ("autostart_success_delay", "REAL DEFAULT 1.8"),
                    ("autostart_error_delay", "REAL DEFAULT 5.0"),
                    ("auto_mic", "INTEGER DEFAULT 1"),
                    ("auto_start", "INTEGER DEFAULT 0"),
                    ("adaptive_snr", "INTEGER DEFAULT 0"),
                    ("vocoder_enabled", "INTEGER DEFAULT 0"),
                    ("vocoder_profile", "TEXT DEFAULT 'medel_12'"),
                    ("voice_en", "TEXT DEFAULT 'Edge-EN-Ava'"),
                    ("exercise_lang", "TEXT DEFAULT 'de'")
                ]:
                    try:
                        cursor.execute(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

                # Automatic migration of words (monosyllables / multisyllables) columns
                for col_name, col_def in [
                    ("list_num", "INTEGER DEFAULT 1"),
                    ("syllables", "TEXT"),
                    ("syllable_count", "INTEGER DEFAULT 1"),
                    ("stress", "TEXT"),
                    ("hint", "TEXT")
                ]:
                    try:
                        cursor.execute(f"ALTER TABLE exercises_words ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

                # Automatic migration of numbers columns
                for col_name, col_def in [
                    ("list_num", "INTEGER DEFAULT 0")
                ]:
                    try:
                        cursor.execute(f"ALTER TABLE exercises_numbers ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

                # Automatic migration of language & translation columns
                for tbl in ["exercises_minimal_pairs", "exercises_words", "exercises_numbers", "exercises_sentences"]:
                    try:
                        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN language TEXT DEFAULT 'de'")
                    except Exception:
                        pass
                    try:
                        cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN translation_de TEXT")
                    except Exception:
                        pass
                try:
                    cursor.execute("ALTER TABLE exercises_minimal_pairs ADD COLUMN translation_a TEXT")
                except Exception:
                    pass
                try:
                    cursor.execute("ALTER TABLE exercises_minimal_pairs ADD COLUMN translation_b TEXT")
                except Exception:
                    pass

                # Update English minimal pairs translations for existing databases
                try:
                    en_mp_path = get_resource_path("data/minimal_pairs_en.json")
                    if en_mp_path.exists():
                        with open(en_mp_path, "r", encoding="utf-8") as f:
                            en_items = json.load(f)
                        for item in en_items:
                            item_id = item.get("id")
                            trans_a = item.get("translation_a") or ""
                            trans_b = item.get("translation_b") or ""
                            trans_de = item.get("translation_de") or (f"{trans_a} / {trans_b}" if trans_a and trans_b else trans_a)
                            wa = item.get("word_a")
                            wb = item.get("word_b")
                            if (trans_a or trans_b):
                                cursor.execute("""
                                    UPDATE exercises_minimal_pairs
                                    SET translation_a = ?, translation_b = ?, translation_de = ?
                                    WHERE id = ? OR (word_a = ? AND word_b = ?)
                                """, (trans_a, trans_b, trans_de, item_id, wa, wb))
                except Exception as e:
                    logger.error(f"[DB Migration Error]: {e}")

                conn.commit()

    # ─── INITIAL SEEDING ───────────────────────────────────────────────────────

    def _seed_if_empty(self):
        """Seeds SQLite tables from JSON data files when the tables are empty or need standard catalog sync."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # ── Minimal Pairs ────────────────────────────────────────────────
                mp_file = get_resource_path("data/minimal_pairs.json")
                cursor.execute("SELECT COUNT(*) FROM exercises_minimal_pairs")
                if cursor.fetchone()[0] == 0 and mp_file.exists():
                    try:
                        with open(mp_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                        for idx, item in enumerate(items):
                            item_id = item.get("id") or f"mp_{idx+1}_{uuid.uuid4().hex[:4]}"
                            opts_j = json.dumps(item["options"], ensure_ascii=False) if item.get("options") else None
                            cursor.execute("""
                                INSERT OR IGNORE INTO exercises_minimal_pairs
                                    (id, category, source, options_json, word_a, word_b, difficulty, hint)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item_id,
                                item.get("category", "Allgemein"),
                                item.get("source", "Marburger Minimalpaar-Katalog"),
                                opts_j,
                                item.get("word_a"),
                                item.get("word_b"),
                                item.get("difficulty", "Mittel"),
                                item.get("hint"),
                            ))
                        logger.info(f"[DB] Seeded {len(items)} minimal pairs.")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding minimal pairs: {e}")

                # ── Words: Monosyllables & Multisyllables ────────────────────────
                mo_file = get_resource_path("data/monosyllables.json")
                cursor.execute("SELECT COUNT(*) FROM exercises_words WHERE source LIKE '%Freiburger%'")
                din_mono_count = cursor.fetchone()[0]
                if (din_mono_count < 400) and mo_file.exists():
                    try:
                        with open(mo_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                        for idx, item in enumerate(items):
                            item_id = item.get("id") or f"mo_{idx+1}_{uuid.uuid4().hex[:4]}"
                            cursor.execute("""
                                INSERT OR REPLACE INTO exercises_words
                                    (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item_id,
                                item.get("word", ""),
                                item.get("category", "Einsilber"),
                                item.get("source", "Freiburger Einsilber-Test (DIN 45621)"),
                                item.get("difficulty", "Einfach"),
                                item.get("list_num", (idx // 20) + 1),
                                item.get("syllables", item.get("word", "")),
                                item.get("syllable_count", 1),
                                item.get("stress", ""),
                                item.get("hint", "")
                            ))
                        logger.info(f"[DB] Seeded {len(items)} DIN 45621 monosyllables across 20 test lists.")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding monosyllables: {e}")

                # Seed Multisyllables & Compound Words
                ms_file = get_resource_path("data/multisyllables.json")
                if ms_file.exists():
                    try:
                        with open(ms_file, "r", encoding="utf-8") as f:
                            ms_items = json.load(f)
                        for idx, item in enumerate(ms_items):
                            item_id = item.get("id") or f"ms_{idx+1}_{uuid.uuid4().hex[:4]}"
                            cursor.execute("""
                                INSERT OR REPLACE INTO exercises_words
                                    (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item_id,
                                item.get("word", ""),
                                item.get("category", "Mehrsilber & Komposita"),
                                item.get("source", "Logopädischer Mehrsilber-Katalog"),
                                item.get("difficulty", item.get("difficulty", "Mittel")),
                                0,
                                item.get("syllables", ""),
                                item.get("syllable_count", 2),
                                item.get("stress", ""),
                                item.get("hint", "")
                            ))
                        logger.info(f"[DB] Seeded {len(ms_items)} multisyllable and compound words.")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding multisyllables: {e}")

                # ── Numbers (including DIN 45621 Number Lists) ────────────────────
                nu_file = get_resource_path("data/numbers.json")
                cursor.execute("SELECT COUNT(*) FROM exercises_numbers WHERE source LIKE '%Freiburger%'")
                din_num_count = cursor.fetchone()[0]
                if (din_num_count < 100) and nu_file.exists():
                    try:
                        with open(nu_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                        for idx, item in enumerate(items):
                            item_id = item.get("id") or f"nu_{idx+1}_{uuid.uuid4().hex[:4]}"
                            cursor.execute("""
                                INSERT OR REPLACE INTO exercises_numbers
                                    (id, type, source, value, spoken, difficulty, list_num)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item_id,
                                item.get("type") or item.get("category") or "Einfache Zahlen",
                                item.get("source", "Audiologischer Zahlen- & Uhrzeitentest"),
                                item.get("value", ""),
                                item.get("spoken", ""),
                                item.get("difficulty", "Einfach"),
                                item.get("list_num", 0)
                            ))
                        logger.info(f"[DB] Seeded {len(items)} numbers (including DIN 45621 test lists).")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding numbers: {e}")

                # ── Sentences ────────────────────────────────────────────────────
                se_file = get_resource_path("data/sentences.json")
                cursor.execute("SELECT COUNT(*) FROM exercises_sentences")
                if cursor.fetchone()[0] == 0 and se_file.exists():
                    try:
                        with open(se_file, "r", encoding="utf-8") as f:
                            items = json.load(f)
                        for idx, item in enumerate(items):
                            item_id = item.get("id") or f"se_{idx+1}_{uuid.uuid4().hex[:4]}"
                            opts_j = json.dumps(item.get("options", []), ensure_ascii=False)
                            cursor.execute("""
                                INSERT OR IGNORE INTO exercises_sentences
                                    (id, category, source, sentence, target_word, options_json, hint)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item_id,
                                item.get("category", "Alltagssätze"),
                                item.get("source", "Oldenburger Satztest (OLSA)"),
                                item.get("sentence", ""),
                                item.get("target_word", ""),
                                opts_j,
                                item.get("hint"),
                            ))
                        logger.info(f"[DB] Seeded {len(items)} sentences.")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding sentences: {e}")

                # ── English Datasets Seeding ─────────────────────────────────────
                for en_file_name, table_name, seed_type in [
                    ("data/minimal_pairs_en.json", "exercises_minimal_pairs", "minimal_pairs"),
                    ("data/monosyllables_en.json", "exercises_words", "words"),
                    ("data/multisyllables_en.json", "exercises_words", "words"),
                    ("data/numbers_en.json", "exercises_numbers", "numbers"),
                    ("data/sentences_en.json", "exercises_sentences", "sentences"),
                ]:
                    en_path = get_resource_path(en_file_name)
                    if en_path.exists():
                        try:
                            with open(en_path, "r", encoding="utf-8") as f:
                                en_items = json.load(f)
                            for idx, item in enumerate(en_items):
                                item_id = item.get("id") or f"en_{seed_type}_{idx+1}"
                                if seed_type == "minimal_pairs":
                                    opts_j = json.dumps(item.get("options", []), ensure_ascii=False) if item.get("options") else None
                                    trans_a = item.get("translation_a") or ""
                                    trans_b = item.get("translation_b") or ""
                                    trans_de = item.get("translation_de") or (f"{trans_a} / {trans_b}" if trans_a and trans_b else trans_a)
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO exercises_minimal_pairs
                                            (id, category, source, options_json, word_a, word_b, difficulty, hint, language, translation_de, translation_a, translation_b)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'en', ?, ?, ?)
                                    """, (item_id, item.get("category"), "English Clinical Catalog", opts_j, item.get("word_a"), item.get("word_b"), item.get("difficulty", "Mittel"), item.get("hint"), trans_de, trans_a, trans_b))
                                elif seed_type == "words":
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO exercises_words
                                            (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint, language, translation_de)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en', ?)
                                    """, (item_id, item.get("word"), item.get("category"), item.get("source", "CNC / Spondee English Catalog"), item.get("difficulty", "Einfach"), item.get("list_num", 1), item.get("syllables", item.get("word")), item.get("syllable_count", 1), item.get("stress", ""), item.get("hint", ""), item.get("translation_de")))
                                elif seed_type == "numbers":
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO exercises_numbers
                                            (id, type, source, value, spoken, difficulty, list_num, language, translation_de)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?)
                                    """, (item_id, item.get("category", "Einzelzahlen"), "English Audiometric Numbers", item.get("text", item.get("value", "")), item.get("spoken", ""), item.get("difficulty", "Einfach"), 0, item.get("translation_de")))
                                elif seed_type == "sentences":
                                    opts_j = json.dumps(item.get("options_json", []), ensure_ascii=False) if isinstance(item.get("options_json"), list) else item.get("options_json", "[]")
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO exercises_sentences
                                            (id, category, source, sentence, target_word, options_json, hint, language, translation_de)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, 'en', ?)
                                    """, (item_id, item.get("category"), "English Matrix / Daily Sentences", item.get("text", item.get("sentence", "")), item.get("word_focus", item.get("target_word", "")), opts_j, item.get("hint"), item.get("translation_de")))
                            logger.info(f"[DB] Seeded {len(en_items)} English {seed_type} items.")
                        except Exception as e:
                            logger.error(f"[DB] Error seeding English dataset {en_file_name}: {e}")

                # ── Default User Profile ─────────────────────────────────────────
                cursor.execute("SELECT COUNT(*) FROM user_profiles")
                if cursor.fetchone()[0] == 0:
                    try:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        cursor.execute("""
                            INSERT INTO user_profiles
                                (id, name, fitting_type, implant_model, first_fitting_date,
                                 audio_balance, master_gain, speech_rate, voice, mask_noise,
                                 noise_volume, is_active, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            "prof_default_1",
                            "Standard Profil",
                            "bilateral",
                            "Cochlear Nucleus 8",
                            today_str,
                            0.0,
                            1.0,
                            1.0,
                            "Anna",
                            0,
                            0.4,
                            1,
                            now_str,
                            now_str
                        ))
                        logger.info("[DB] Seeded default user profile.")
                    except Exception as e:
                        logger.error(f"[DB] Error seeding default profile: {e}")

                conn.commit()

    # ─── READ ALL EXERCISES ────────────────────────────────────────────────────

    def get_all_exercises(self, lang: str = "de") -> dict:
        """
        Returns all exercises from the database grouped by type and filtered by language ('de' or 'en').
        The structure is fully backwards-compatible with the old JSON-based API.
        """
        res = {
            "minimal_pairs": [],
            "monosyllables": [],
            "numbers": [],
            "sentences": [],
        }

        lang_code = 'en' if (lang or 'de').lower().startswith('en') else 'de'

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Minimal Pairs
                cursor.execute(
                    "SELECT id, category, source, options_json, word_a, word_b, difficulty, hint, translation_de, translation_a, translation_b"
                    " FROM exercises_minimal_pairs WHERE (language = ? OR (language IS NULL AND ? = 'de'))",
                    (lang_code, lang_code)
                )
                for row in cursor.fetchall():
                    item_id, cat, src, opts_j, wa, wb, diff, hint, trans_de, trans_a, trans_b = row
                    item: dict = {
                        "id": item_id,
                        "category": cat,
                        "source": src,
                        "difficulty": diff,
                        "hint": hint,
                        "translation_de": trans_de or "",
                        "translation_a": trans_a or "",
                        "translation_b": trans_b or "",
                    }
                    if opts_j:
                        try:
                            item["options"] = json.loads(opts_j)
                        except Exception:
                            item["options"] = []
                    if wa:
                        item["word_a"] = wa
                    if wb:
                        item["word_b"] = wb
                    res["minimal_pairs"].append(item)

                # 2. Words (Monosyllables, Multisyllables, Compound Words)
                cursor.execute(
                    "SELECT id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint, translation_de"
                    " FROM exercises_words WHERE (language = ? OR (language IS NULL AND ? = 'de'))",
                    (lang_code, lang_code)
                )
                for row in cursor.fetchall():
                    item_id, word, cat, src, diff, list_num, syls, syl_cnt, stress, hint, trans_de = row
                    res["monosyllables"].append({
                        "id": item_id,
                        "word": word,
                        "category": cat,
                        "source": src,
                        "difficulty": diff,
                        "list_num": list_num or 0,
                        "syllables": syls or word,
                        "syllable_count": syl_cnt or 1,
                        "stress": stress or "",
                        "hint": hint or "",
                        "translation_de": trans_de or "",
                    })

                # 3. Numbers
                cursor.execute(
                    "SELECT id, type, source, value, spoken, difficulty, list_num, translation_de FROM exercises_numbers"
                    " WHERE (language = ? OR (language IS NULL AND ? = 'de'))",
                    (lang_code, lang_code)
                )
                for row in cursor.fetchall():
                    item_id, num_type, src, val, spoken, diff, list_num, trans_de = row
                    res["numbers"].append({
                        "id": item_id,
                        "type": num_type,
                        "category": num_type,
                        "source": src,
                        "value": val,
                        "spoken": spoken,
                        "difficulty": diff,
                        "list_num": list_num or 0,
                        "translation_de": trans_de or "",
                    })

                # 4. Sentences
                cursor.execute(
                    "SELECT id, category, source, sentence, target_word, options_json, hint, translation_de"
                    " FROM exercises_sentences WHERE (language = ? OR (language IS NULL AND ? = 'de'))",
                    (lang_code, lang_code)
                )
                for row in cursor.fetchall():
                    item_id, cat, src, sentence, target, opts_j, hint, trans_de = row
                    opts = []
                    if opts_j:
                        try:
                            opts = json.loads(opts_j)
                        except Exception:
                            opts = []
                    res["sentences"].append({
                        "id": item_id,
                        "category": cat,
                        "source": src,
                        "sentence": sentence,
                        "text": sentence,
                        "target_word": target,
                        "word_focus": target,
                        "options": opts,
                        "hint": hint or "",
                        "translation_de": trans_de or "",
                    })

            return res

    # ─── CREATE ───────────────────────────────────────────────────────────────

    def add_exercise(self, mod_type: str, item: dict) -> dict:
        """Inserts a new exercise into the corresponding table and returns it with its assigned ID."""
        item_id = item.get("id") or f"{mod_type[:2]}_{uuid.uuid4().hex[:6]}"
        item = dict(item)  # do not mutate caller's dict
        item["id"] = item_id

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if mod_type == "minimal_pairs":
                    opts_j = json.dumps(item.get("options", []), ensure_ascii=False) if item.get("options") is not None else None
                    cursor.execute("""
                        INSERT INTO exercises_minimal_pairs
                            (id, category, source, options_json, word_a, word_b, difficulty, hint)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        item.get("category", "Allgemein"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        opts_j,
                        item.get("word_a"),
                        item.get("word_b"),
                        item.get("difficulty", "Mittel"),
                        item.get("hint"),
                    ))

                elif mod_type in ("monosyllables", "multisyllables", "words"):
                    cursor.execute("""
                        INSERT INTO exercises_words
                            (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        item.get("word", ""),
                        item.get("category", "Einsilber"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("difficulty", "Einfach"),
                        item.get("list_num", 0),
                        item.get("syllables", item.get("word", "")),
                        item.get("syllable_count", 1),
                        item.get("stress", ""),
                        item.get("hint", ""),
                    ))

                elif mod_type == "numbers":
                    cursor.execute("""
                        INSERT INTO exercises_numbers
                            (id, type, source, value, spoken, difficulty)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        item.get("type") or item.get("category") or "Einfache Zahlen",
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("value", ""),
                        item.get("spoken", ""),
                        item.get("difficulty", "Einfach"),
                    ))

                elif mod_type == "sentences":
                    opts_j = json.dumps(item.get("options", []), ensure_ascii=False)
                    cursor.execute("""
                        INSERT INTO exercises_sentences
                            (id, category, source, sentence, target_word, options_json, hint)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item_id,
                        item.get("category", "Alltagssätze"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("sentence", ""),
                        item.get("target_word", ""),
                        opts_j,
                        item.get("hint"),
                    ))

                else:
                    raise ValueError(f"Unknown module type: {mod_type!r}")

                conn.commit()

        return item

    # ─── UPDATE ───────────────────────────────────────────────────────────────

    def update_exercise(self, mod_type: str, item: dict) -> bool:
        """Updates an existing exercise by ID.  Returns True when a row was changed."""
        item_id = item.get("id")
        if not item_id:
            return False

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if mod_type == "minimal_pairs":
                    opts_j = json.dumps(item.get("options", []), ensure_ascii=False) if item.get("options") is not None else None
                    cursor.execute("""
                        UPDATE exercises_minimal_pairs
                        SET category=?, source=?, options_json=?, word_a=?, word_b=?, difficulty=?, hint=?
                        WHERE id=?
                    """, (
                        item.get("category", "Allgemein"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        opts_j,
                        item.get("word_a"),
                        item.get("word_b"),
                        item.get("difficulty", "Mittel"),
                        item.get("hint"),
                        item_id,
                    ))

                elif mod_type in ("monosyllables", "multisyllables", "words"):
                    cursor.execute("""
                        UPDATE exercises_words
                        SET word=?, category=?, source=?, difficulty=?, list_num=?, syllables=?, syllable_count=?, stress=?, hint=?
                        WHERE id=?
                    """, (
                        item.get("word", ""),
                        item.get("category", "Einsilber"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("difficulty", "Einfach"),
                        item.get("list_num", 0),
                        item.get("syllables", item.get("word", "")),
                        item.get("syllable_count", 1),
                        item.get("stress", ""),
                        item.get("hint", ""),
                        item_id,
                    ))

                elif mod_type == "numbers":
                    cursor.execute("""
                        UPDATE exercises_numbers
                        SET type=?, source=?, value=?, spoken=?, difficulty=?
                        WHERE id=?
                    """, (
                        item.get("type") or item.get("category") or "Einfache Zahlen",
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("value", ""),
                        item.get("spoken", ""),
                        item.get("difficulty", "Einfach"),
                        item_id,
                    ))

                elif mod_type == "sentences":
                    opts_j = json.dumps(item.get("options", []), ensure_ascii=False)
                    cursor.execute("""
                        UPDATE exercises_sentences
                        SET category=?, source=?, sentence=?, target_word=?, options_json=?, hint=?
                        WHERE id=?
                    """, (
                        item.get("category", "Alltagssätze"),
                        item.get("source", "Eigenes Übungsmaterial"),
                        item.get("sentence", ""),
                        item.get("target_word", ""),
                        opts_j,
                        item.get("hint"),
                        item_id,
                    ))

                else:
                    return False

                conn.commit()
                return cursor.rowcount > 0

    # ─── DELETE ───────────────────────────────────────────────────────────────

    def delete_exercise(self, mod_type: str, item_id: str) -> bool:
        """Deletes an exercise by ID.  Returns True when a row was removed."""
        table_map = {
            "minimal_pairs": "exercises_minimal_pairs",
            "monosyllables": "exercises_words",
            "multisyllables": "exercises_words",
            "words": "exercises_words",
            "numbers": "exercises_numbers",
            "sentences": "exercises_sentences",
        }
        table_name = table_map.get(mod_type)
        if not table_name:
            return False

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (item_id,))
                conn.commit()
                return cursor.rowcount > 0

    # ─── CATEGORY MANAGEMENT & BULK OPERATIONS ────────────────────────────────

    def rename_category(self, mod_type: str, old_cat: str, new_cat: str) -> int:
        """Renames a category across all exercises of a given module type."""
        table_map = {
            "minimal_pairs": ("exercises_minimal_pairs", "category"),
            "monosyllables": ("exercises_words", "category"),
            "multisyllables": ("exercises_words", "category"),
            "words": ("exercises_words", "category"),
            "numbers": ("exercises_numbers", "type"),
            "sentences": ("exercises_sentences", "category"),
        }
        info = table_map.get(mod_type)
        if not info or not old_cat or not new_cat:
            return 0
        table_name, col_name = info

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE {table_name} SET {col_name}=? WHERE {col_name}=?",
                    (new_cat.strip(), old_cat.strip()),
                )
                conn.commit()
                return cursor.rowcount

    def delete_category(self, mod_type: str, category: str, only_custom: bool = True) -> int:
        """Deletes all exercises in a given category (default: only custom/non-standard)."""
        table_map = {
            "minimal_pairs": ("exercises_minimal_pairs", "category"),
            "monosyllables": ("exercises_words", "category"),
            "multisyllables": ("exercises_words", "category"),
            "words": ("exercises_words", "category"),
            "numbers": ("exercises_numbers", "type"),
            "sentences": ("exercises_sentences", "category"),
        }
        info = table_map.get(mod_type)
        if not info or not category:
            return 0
        table_name, col_name = info

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if only_custom:
                    cursor.execute(
                        f"DELETE FROM {table_name} WHERE {col_name}=? AND source LIKE '%Eigenes%'",
                        (category.strip(),),
                    )
                else:
                    cursor.execute(
                        f"DELETE FROM {table_name} WHERE {col_name}=?",
                        (category.strip(),),
                    )
                conn.commit()
                return cursor.rowcount

    def bulk_add_exercises(self, mod_type: str, items: list) -> list:
        """Inserts multiple custom exercises in a single transaction, skipping standard catalog duplicates."""
        standard_sources = {
            "Marburger Minimalpaar-Katalog",
            "Logopädischer Minimalpaar-Katalog",
            "Freiburger Einsilber-Test (DIN 45621)",
            "Freiburger Einsilber-Test",
            "Audiologischer Zahlen- & Uhrzeitentest",
            "Oldenburger Satztest (OLSA)",
            "DIN 45621"
        }
        added = []
        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue
            item = dict(raw_item)
            src = (item.get("source") or "").strip()
            # Reject items with standard source
            if src in standard_sources:
                continue

            # Ensure custom source if blank
            if not src or "Eigen" not in src:
                item["source"] = "Eigenes Übungsmaterial (Import)"

            # Ensure unique custom ID
            item_id = str(item.get("id") or "")
            if not item_id.startswith("cu_"):
                item["id"] = f"cu_{mod_type[:2]}_{uuid.uuid4().hex[:6]}"

            created = self.add_exercise(mod_type, item)
            added.append(created)
        return added

    # ─── STATISTICAL LOGGING ──────────────────────────────────────────────────

    def log_attempt(
        self,
        module: str,
        category: str,
        target_word: str,
        user_answer: str,
        is_correct: bool,
        score: float,
        snr_db: float = 0.0,
    ):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO training_logs
                        (timestamp, module, category, target_word, user_answer, is_correct, score, snr_db)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    module,
                    category,
                    target_word,
                    user_answer,
                    1 if is_correct else 0,
                    score,
                    snr_db,
                ))
                conn.commit()

    def reset_stats(self):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM training_logs")
                conn.commit()

    def delete_training_log(self, log_id: int) -> bool:
        """Deletes a specific training log entry by id."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM training_logs WHERE id=?", (log_id,))
                conn.commit()
                return cursor.rowcount > 0

    def get_training_logs(self, limit: int = 100, offset: int = 0, module: str = None, filter_status: str = None) -> dict:
        """Returns paginated and filtered training logs."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT id, timestamp, module, category, target_word, user_answer, is_correct, score, snr_db FROM training_logs WHERE 1=1"
                params = []

                if module:
                    query += " AND module = ?"
                    params.append(module)
                if filter_status == "correct":
                    query += " AND is_correct = 1"
                elif filter_status == "wrong":
                    query += " AND is_correct = 0"

                # Count total
                count_query = "SELECT COUNT(*) FROM (" + query + ")"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # Fetch logs
                query += " ORDER BY id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                cursor.execute(query, params)

                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "module": row[2],
                        "category": row[3],
                        "target_word": row[4],
                        "user_answer": row[5],
                        "is_correct": bool(row[6]),
                        "score": row[7],
                        "snr_db": row[8],
                    })

                return {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "logs": logs
                }

    def get_summary_stats(self) -> dict:
        return self.get_stats()

    def get_stats(self) -> dict:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*), SUM(is_correct), AVG(score) FROM training_logs")
                row = cursor.fetchone()
                total = row[0] or 0
                correct = row[1] or 0
                avg_score = row[2] or 0.0

                cursor.execute("""
                    SELECT module, COUNT(*), SUM(is_correct), AVG(score)
                    FROM training_logs
                    GROUP BY module
                """)
                by_module: dict = {}
                for row in cursor.fetchall():
                    mod, count, corr, avg_s = row
                    corr = corr or 0
                    by_module[mod] = {
                        "count": count,
                        "correct": corr,
                        "accuracy": round((corr / count * 100) if count > 0 else 0, 1),
                        "avg_score": round(avg_s or 0.0, 1),
                    }

                cursor.execute("""
                    SELECT category, COUNT(*), SUM(is_correct)
                    FROM training_logs
                    WHERE category IS NOT NULL AND category != ''
                    GROUP BY category
                """)
                by_category: dict = {}
                for row in cursor.fetchall():
                    cat, count, corr = row
                    corr = corr or 0
                    by_category[cat] = {
                        "count": count,
                        "correct": corr,
                        "accuracy": round((corr / count * 100) if count > 0 else 0, 1),
                    }

                return {
                    "total_attempts": total,
                    "correct_attempts": correct,
                    "accuracy": round((correct / total * 100) if total > 0 else 0, 1),
                    "avg_score": round(avg_score, 1),
                    "by_module": by_module,
                    "by_category": by_category,
                }

    def get_therapist_report(self) -> dict:
        """
        Generates a comprehensive clinical progress report for speech therapists (Logopäden)
        and audiologists, aggregating active profile, stats, acoustic category breakdown,
        Freiburger test runs, and OLSA SRT history.
        """
        with self._lock:
            active_profile = self.get_active_profile()
            stats = self.get_stats()
            weaknesses = self.get_weak_exercises()
            test_runs = self.get_test_runs()[:10]
            olsa_runs = self.get_olsa_runs(limit=10)
            curves = self.get_freiburger_curves(limit=5)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(DISTINCT date(timestamp)) FROM training_logs")
                row = cursor.fetchone()
                first_attempt = row[0] or "Keine Daten"
                last_attempt = row[1] or "Keine Daten"
                active_days = row[2] or 0

            return {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "profile": active_profile,
                "summary": {
                    "total_attempts": stats.get("total_attempts", 0),
                    "correct_attempts": stats.get("correct_attempts", 0),
                    "accuracy": stats.get("accuracy", 0.0),
                    "avg_score": stats.get("avg_score", 0.0),
                    "first_attempt": first_attempt,
                    "last_attempt": last_attempt,
                    "active_days": active_days,
                },
                "by_module": stats.get("by_module", {}),
                "by_category": stats.get("by_category", {}),
                "weak_categories": weaknesses.get("weak_categories", []),
                "test_runs": test_runs,
                "olsa_runs": olsa_runs,
                "curves": curves,
            }

    def get_freiburger_test_lists(self) -> dict:
        """Returns monosyllable words grouped into official 20-word Freiburger Testlists (DIN 45621: Listen 1 bis 20)."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, word, category, source, difficulty, list_num
                    FROM exercises_words
                    WHERE source LIKE '%Freiburger%' OR category = 'Einsilber'
                    ORDER BY list_num ASC, rowid ASC
                """)
                rows = cursor.fetchall()
                all_words = [{"id": r[0], "word": r[1], "category": r[2], "source": r[3], "difficulty": r[4], "list_num": r[5]} for r in rows]

            lists = {}
            # Group by list_num if defined (1..20)
            grouped = {}
            for w in all_words:
                ln = w.get("list_num") or 1
                if ln > 0:
                    grouped.setdefault(ln, []).append(w)

            if grouped:
                for ln in sorted(grouped.keys()):
                    l_words = grouped[ln]
                    lists[f"Liste {ln}"] = {
                        "list_num": ln,
                        "title": f"Freiburger Testliste {ln} (DIN 45621)",
                        "word_count": len(l_words),
                        "words": l_words
                    }
            else:
                words_per_list = 20
                list_count = (len(all_words) + words_per_list - 1) // words_per_list
                for idx in range(list_count):
                    list_num = idx + 1
                    start_i = idx * words_per_list
                    end_i = start_i + words_per_list
                    list_words = all_words[start_i:end_i]
                    lists[f"Liste {list_num}"] = {
                        "list_num": list_num,
                        "title": f"Freiburger Testliste {list_num} (DIN 45621)",
                        "word_count": len(list_words),
                        "words": list_words
                    }
            return lists

    def get_freiburger_number_lists(self) -> dict:
        """Returns 10-item DIN 45621 Freiburger two-syllable number lists (Zahlenliste 1 bis 10)."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, type, source, value, spoken, difficulty, list_num
                    FROM exercises_numbers
                    WHERE type = 'Freiburger Zahlentest (DIN 45621)' OR source LIKE '%Freiburger%'
                    ORDER BY list_num ASC, rowid ASC
                """)
                rows = cursor.fetchall()
                all_numbers = [{"id": r[0], "type": r[1], "category": r[1], "source": r[2], "value": r[3], "spoken": r[4], "difficulty": r[5], "list_num": r[6]} for r in rows]

            lists = {}
            grouped = {}
            for n in all_numbers:
                ln = n.get("list_num") or 1
                if ln > 0:
                    grouped.setdefault(ln, []).append(n)

            if grouped:
                for ln in sorted(grouped.keys()):
                    l_nums = grouped[ln]
                    lists[f"Zahlenliste {ln}"] = {
                        "list_num": ln,
                        "title": f"Freiburger Zahlenliste {ln} (DIN 45621)",
                        "count": len(l_nums),
                        "numbers": l_nums
                    }
            else:
                items_per_list = 10
                list_count = (len(all_numbers) + items_per_list - 1) // items_per_list
                for idx in range(list_count):
                    list_num = idx + 1
                    start_i = idx * items_per_list
                    end_i = start_i + items_per_list
                    list_nums = all_numbers[start_i:end_i]
                    lists[f"Zahlenliste {list_num}"] = {
                        "list_num": list_num,
                        "title": f"Freiburger Zahlenliste {list_num} (DIN 45621)",
                        "count": len(list_nums),
                        "numbers": list_nums
                    }
            return lists

    def log_test_run(self, list_name: str, total_words: int, correct_words: int, score: float, details_json: str = None):
        """Logs a completed Freiburger test run into database."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO test_runs (timestamp, list_name, total_words, correct_words, score, details_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (now, list_name, total_words, correct_words, score, details_json))
                conn.commit()

    def get_test_runs(self) -> list:
        """Returns history of all completed test runs."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, list_name, total_words, correct_words, score, details_json
                    FROM test_runs
                    ORDER BY id DESC
                """)
                return [{
                    "id": r[0],
                    "timestamp": r[1],
                    "list_name": r[2],
                    "total_words": r[3],
                    "correct_words": r[4],
                    "score": r[5],
                    "details_json": r[6]
                } for r in cursor.fetchall()]

    def get_weak_exercises(self, limit: int = 15) -> dict:
        """
        Identifies categories with low accuracy (<60%) or high errors from training logs
        and returns a curated list of exercises targeting those weak areas with audiologic rationale notes.
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, COUNT(*), SUM(is_correct), AVG(score)
                    FROM training_logs
                    WHERE category IS NOT NULL AND category != ''
                    GROUP BY category
                    HAVING (CAST(SUM(is_correct) AS FLOAT) / COUNT(*)) < 0.65 OR COUNT(*) - SUM(is_correct) > 1
                    ORDER BY (CAST(SUM(is_correct) AS FLOAT) / COUNT(*)) ASC, COUNT(*) DESC
                """)
                weak_cats = []
                cat_stats = {}
                for row in cursor.fetchall():
                    cat, total_c, corr_c, avg_s = row
                    corr_c = corr_c or 0
                    acc = round((corr_c / total_c * 100.0), 1) if total_c > 0 else 0.0
                    weak_cats.append(cat)
                    cat_stats[cat] = {"accuracy": acc, "errors": total_c - corr_c}

                exercises_pool = []
                all_ex = self.get_all_exercises()

                if weak_cats:
                    for cat in weak_cats:
                        acc = cat_stats[cat]["accuracy"]
                        errs = cat_stats[cat]["errors"]
                        rationale = f"⚠️ Trefferquote bei '{cat}' liegt bei {acc}% ({errs} Fehler)"

                        # Search matching minimal pairs
                        for item in all_ex.get("minimal_pairs", []):
                            if item.get("category") == cat or cat in item.get("category", ""):
                                exercises_pool.append({**item, "mod_type": "minimal_pairs", "rationale": rationale})

                        # Search matching sentences
                        for item in all_ex.get("sentences", []):
                            if item.get("category") == cat or cat in item.get("category", ""):
                                exercises_pool.append({**item, "mod_type": "sentences", "rationale": rationale})

                # Fallback / General Diagnostic Pool if weak categories are insufficient
                if len(exercises_pool) < limit:
                    rationale = "🔍 Diagnose-Übung: Erfasse deine persönliche Trefferquote"
                    for mod_key in ["minimal_pairs", "monosyllables", "numbers", "sentences"]:
                        items = all_ex.get(mod_key, [])
                        for item in items[:4]:
                            if not any(e.get("id") == item.get("id") for e in exercises_pool):
                                exercises_pool.append({**item, "mod_type": mod_key, "rationale": rationale})

                return {
                    "weak_categories": weak_cats,
                    "count": len(exercises_pool[:limit]),
                    "exercises": exercises_pool[:limit]
                }

    # ─── ADAPTIVE OLSA & FREIBURGER AUDIOGRAM LOGGING ──────────────────────────

    def log_olsa_run(self, srt_db: float, initial_snr: float, noise_type: str, 
                     total_sentences: int, std_dev: float, history: list) -> int:
        """Speichert einen vollständigen adaptiven OLSA-Durchlauf thread-safe."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_json = json.dumps(history, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO olsa_test_runs 
                    (timestamp, srt_db, initial_snr, noise_type, total_sentences, std_dev, history_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ts, srt_db, initial_snr, noise_type, total_sentences, std_dev, history_json))
                conn.commit()
                return cursor.lastrowid

    def get_olsa_runs(self, limit: int = 50) -> list:
        """Gibt die Historie der adaptiven OLSA-Sprachverstehenstests zurück."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, srt_db, initial_snr, noise_type, total_sentences, std_dev, history_json
                    FROM olsa_test_runs
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                runs = []
                for row in cursor.fetchall():
                    r_id, ts, srt, init_snr, ntype, nsent, sdev, h_json = row
                    try:
                        hist = json.loads(h_json) if h_json else []
                    except Exception:
                        hist = []
                    runs.append({
                        "id": r_id,
                        "timestamp": ts,
                        "srt_db": srt,
                        "initial_snr": init_snr,
                        "noise_type": ntype,
                        "total_sentences": nsent,
                        "std_dev": sdev,
                        "history": hist
                    })
                return runs

    def log_freiburger_curve(self, list_name: str, test_data: list, 
                             v_max: float, disc_loss: float, notes: str = "") -> int:
        """Speichert eine Mehrpegel-Freiburger Sprachverstehens-Kurve."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                test_data_json = json.dumps(test_data, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO freiburger_audiograms
                    (timestamp, list_name, test_data_json, v_max, disc_loss, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ts, list_name, test_data_json, v_max, disc_loss, notes))
                conn.commit()
                return cursor.lastrowid

    def get_freiburger_curves(self, limit: int = 50) -> list:
        """Gibt die gespeicherten Freiburger-Sprachaudiometriekurven zurück."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, list_name, test_data_json, v_max, disc_loss, notes
                    FROM freiburger_audiograms
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                curves = []
                for row in cursor.fetchall():
                    c_id, ts, lname, d_json, vmax, dloss, notes = row
                    try:
                        d_points = json.loads(d_json) if d_json else []
                    except Exception:
                        d_points = []
                    curves.append({
                        "id": c_id,
                        "timestamp": ts,
                        "list_name": lname,
                        "test_data": d_points,
                        "v_max": vmax,
                        "disc_loss": dloss,
                        "notes": notes
                    })
                return curves

    # ─── MULTI-USER & CI-SPECIFIC PROFILES ─────────────────────────────────────

    def get_profiles(self) -> list:
        """Returns all user profiles with settings."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, fitting_type, implant_model, first_fitting_date,
                           audio_balance, master_gain, speech_rate, voice, mask_noise,
                           noise_volume, freq_filter, autostart_success_delay, autostart_error_delay,
                           auto_mic, is_active, created_at, updated_at, voice_en, exercise_lang,
                           auto_start, adaptive_snr, vocoder_enabled, vocoder_profile
                    FROM user_profiles
                    ORDER BY is_active DESC, name ASC
                """)
                profiles = []
                for row in cursor.fetchall():
                    (p_id, name, f_type, i_model, f_date,
                     bal, gain, rate, voice, mask_n,
                     n_vol, f_filt, a_succ, a_err,
                     a_mic, is_act, c_at, u_at,
                     v_en, e_lang,
                     a_start, a_snr, v_ena, v_prof) = row
                    profiles.append({
                        "id": p_id,
                        "name": name,
                        "fitting_type": f_type or "bilateral",
                        "implant_model": i_model or "Cochlear Nucleus 8",
                        "first_fitting_date": f_date or "",
                        "audio_balance": float(bal if bal is not None else 0.0),
                        "master_gain": float(gain if gain is not None else 1.0),
                        "speech_rate": float(rate if rate is not None else 1.0),
                        "voice": voice or "Anna",
                        "voice_en": v_en or "Edge-EN-Ava",
                        "exercise_lang": e_lang or "de",
                        "mask_noise": bool(mask_n),
                        "noise_volume": float(n_vol if n_vol is not None else 0.4),
                        "freq_filter": f_filt or "none",
                        "autostart_success_delay": float(a_succ if a_succ is not None else 1.8),
                        "autostart_error_delay": float(a_err if a_err is not None else 5.0),
                        "auto_mic": bool(a_mic if a_mic is not None else 1),
                        "auto_start": bool(a_start if a_start is not None else 0),
                        "adaptive_snr": bool(a_snr if a_snr is not None else 0),
                        "vocoder_enabled": bool(v_ena if v_ena is not None else 0),
                        "vocoder_profile": v_prof or "medel_12",
                        "is_active": bool(is_act),
                        "created_at": c_at,
                        "updated_at": u_at
                    })
                return profiles

    def get_active_profile(self) -> dict:
        """Returns the currently active profile or fallback default."""
        profiles = self.get_profiles()
        for p in profiles:
            if p.get("is_active"):
                return p
        if profiles:
            # Set first profile active if none is marked
            self.set_active_profile(profiles[0]["id"])
            profiles[0]["is_active"] = True
            return profiles[0]
        # Fallback if no profiles exist
        return {
            "id": "prof_default_1",
            "name": "Standard Profil",
            "fitting_type": "bilateral",
            "implant_model": "Cochlear Nucleus 8",
            "first_fitting_date": datetime.now().strftime("%Y-%m-%d"),
            "audio_balance": 0.0,
            "master_gain": 1.0,
            "speech_rate": 1.0,
            "voice": "Anna",
            "voice_en": "Edge-EN-Ava",
            "exercise_lang": "de",
            "mask_noise": False,
            "noise_volume": 0.4,
            "freq_filter": "none",
            "autostart_success_delay": 1.8,
            "autostart_error_delay": 5.0,
            "auto_mic": True,
            "auto_start": False,
            "adaptive_snr": False,
            "vocoder_enabled": False,
            "vocoder_profile": "medel_12",
            "is_active": True
        }

    def create_profile(self, data: dict) -> dict:
        """Creates a new user profile."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                p_id = data.get("id") or f"prof_{uuid.uuid4().hex[:8]}"
                name = str(data.get("name") or "Neues Profil").strip()
                f_type = str(data.get("fitting_type") or "bilateral").strip()
                i_model = str(data.get("implant_model") or "Cochlear Nucleus 8").strip()
                f_date = str(data.get("first_fitting_date") or datetime.now().strftime("%Y-%m-%d")).strip()
                bal = float(data.get("audio_balance", 0.0))
                gain = float(data.get("master_gain", 1.0))
                rate = float(data.get("speech_rate", 1.0))
                voice = str(data.get("voice") or "Anna")
                v_en = str(data.get("voice_en") or "Edge-EN-Ava")
                e_lang = str(data.get("exercise_lang") or "de")
                mask_n = 1 if data.get("mask_noise") else 0
                n_vol = float(data.get("noise_volume", 0.4))
                f_filt = str(data.get("freq_filter") or "none")
                a_succ = float(data.get("autostart_success_delay", 1.8))
                a_err = float(data.get("autostart_error_delay", 5.0))
                a_mic = 1 if data.get("auto_mic", True) else 0
                a_start = 1 if data.get("auto_start") else 0
                a_snr = 1 if data.get("adaptive_snr") else 0
                v_ena = 1 if data.get("vocoder_enabled") else 0
                v_prof = str(data.get("vocoder_profile") or "medel_12")
                is_act = 1 if data.get("is_active") else 0

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if is_act:
                    cursor.execute("UPDATE user_profiles SET is_active = 0")

                cursor.execute("""
                    INSERT INTO user_profiles
                        (id, name, fitting_type, implant_model, first_fitting_date,
                         audio_balance, master_gain, speech_rate, voice, voice_en, exercise_lang, mask_noise,
                         noise_volume, freq_filter, autostart_success_delay, autostart_error_delay,
                         auto_mic, auto_start, adaptive_snr, vocoder_enabled, vocoder_profile, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_id, name, f_type, i_model, f_date,
                    bal, gain, rate, voice, v_en, e_lang, mask_n,
                    n_vol, f_filt, a_succ, a_err,
                    a_mic, a_start, a_snr, v_ena, v_prof, is_act, now_str, now_str
                ))
                conn.commit()

                return {
                    "id": p_id,
                    "name": name,
                    "fitting_type": f_type,
                    "implant_model": i_model,
                    "first_fitting_date": f_date,
                    "audio_balance": bal,
                    "master_gain": gain,
                    "speech_rate": rate,
                    "voice": voice,
                    "voice_en": v_en,
                    "exercise_lang": e_lang,
                    "mask_noise": bool(mask_n),
                    "noise_volume": n_vol,
                    "freq_filter": f_filt,
                    "autostart_success_delay": a_succ,
                    "autostart_error_delay": a_err,
                    "auto_mic": bool(a_mic),
                    "auto_start": bool(a_start),
                    "adaptive_snr": bool(a_snr),
                    "vocoder_enabled": bool(v_ena),
                    "vocoder_profile": v_prof,
                    "is_active": bool(is_act),
                    "created_at": now_str,
                    "updated_at": now_str
                }

    def update_profile(self, profile_id: str, data: dict) -> dict:
        """Updates an existing profile."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user_profiles WHERE id = ?", (profile_id,))
                if not cursor.fetchone():
                    return {}

                fields = []
                params = []

                if "name" in data:
                    fields.append("name = ?")
                    params.append(str(data["name"]).strip())
                if "fitting_type" in data:
                    fields.append("fitting_type = ?")
                    params.append(str(data["fitting_type"]).strip())
                if "implant_model" in data:
                    fields.append("implant_model = ?")
                    params.append(str(data["implant_model"]).strip())
                if "first_fitting_date" in data:
                    fields.append("first_fitting_date = ?")
                    params.append(str(data["first_fitting_date"]).strip())
                if "audio_balance" in data:
                    fields.append("audio_balance = ?")
                    params.append(float(data["audio_balance"]))
                if "master_gain" in data:
                    fields.append("master_gain = ?")
                    params.append(float(data["master_gain"]))
                if "speech_rate" in data:
                    fields.append("speech_rate = ?")
                    params.append(float(data["speech_rate"]))
                if "voice" in data:
                    fields.append("voice = ?")
                    params.append(str(data["voice"]))
                if "voice_en" in data:
                    fields.append("voice_en = ?")
                    params.append(str(data["voice_en"]))
                if "exercise_lang" in data:
                    fields.append("exercise_lang = ?")
                    params.append(str(data["exercise_lang"]))
                if "mask_noise" in data:
                    fields.append("mask_noise = ?")
                    params.append(1 if data["mask_noise"] else 0)
                if "noise_volume" in data:
                    fields.append("noise_volume = ?")
                    params.append(float(data["noise_volume"]))
                if "freq_filter" in data:
                    fields.append("freq_filter = ?")
                    params.append(str(data["freq_filter"]))
                if "autostart_success_delay" in data:
                    fields.append("autostart_success_delay = ?")
                    params.append(float(data["autostart_success_delay"]))
                if "autostart_error_delay" in data:
                    fields.append("autostart_error_delay = ?")
                    params.append(float(data["autostart_error_delay"]))
                if "auto_mic" in data:
                    fields.append("auto_mic = ?")
                    params.append(1 if data["auto_mic"] else 0)
                if "auto_start" in data:
                    fields.append("auto_start = ?")
                    params.append(1 if data["auto_start"] else 0)
                if "adaptive_snr" in data:
                    fields.append("adaptive_snr = ?")
                    params.append(1 if data["adaptive_snr"] else 0)
                if "vocoder_enabled" in data:
                    fields.append("vocoder_enabled = ?")
                    params.append(1 if data["vocoder_enabled"] else 0)
                if "vocoder_profile" in data:
                    fields.append("vocoder_profile = ?")
                    params.append(str(data["vocoder_profile"]))

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fields.append("updated_at = ?")
                params.append(now_str)

                params.append(profile_id)
                query = f"UPDATE user_profiles SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, tuple(params))
                conn.commit()

                for p in self.get_profiles():
                    if p["id"] == profile_id:
                        return p
                return {}

    def set_active_profile(self, profile_id: str) -> bool:
        """Sets the given profile as active and deactivates all others."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM user_profiles WHERE id = ?", (profile_id,))
                if not cursor.fetchone():
                    return False
                cursor.execute("UPDATE user_profiles SET is_active = 0")
                cursor.execute("UPDATE user_profiles SET is_active = 1, updated_at = ? WHERE id = ?",
                               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), profile_id))
                conn.commit()
                return True

    def delete_profile(self, profile_id: str) -> bool:
        """Deletes a profile. Ensures at least one profile remains."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_profiles")
                total = cursor.fetchone()[0]
                if total <= 1:
                    return False  # Cannot delete the only profile

                cursor.execute("SELECT is_active FROM user_profiles WHERE id = ?", (profile_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                was_active = bool(row[0])

                cursor.execute("DELETE FROM user_profiles WHERE id = ?", (profile_id,))

                if was_active:
                    # Activate another remaining profile
                    cursor.execute("SELECT id FROM user_profiles LIMIT 1")
                    next_id = cursor.fetchone()[0]
                    cursor.execute("UPDATE user_profiles SET is_active = 1 WHERE id = ?", (next_id,))

                conn.commit()
                return True



