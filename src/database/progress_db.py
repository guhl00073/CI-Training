import sqlite3
import pathlib
import json
import os
import uuid
import threading
from datetime import datetime


class ProgressDatabase:
    """
    SQLite Database Manager for tracking CI hearing training progress,
    statistics, and exercise catalog (Minimal pairs, Monosyllables, Numbers, Sentences).
    """

    def __init__(self, db_path: str = "data/ci-training.db"):
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

            # 3. Exercises: Monosyllables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises_monosyllables (
                    id TEXT PRIMARY KEY,
                    word TEXT NOT NULL,
                    category TEXT DEFAULT 'Einsilber',
                    source TEXT DEFAULT 'Freiburger Einsilber-Test (DIN 45621)',
                    difficulty TEXT DEFAULT 'Einfach'
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
                    test_name TEXT NOT NULL,
                    list_num INTEGER NOT NULL,
                    total_words INTEGER NOT NULL,
                    correct_words INTEGER NOT NULL,
                    score_percent REAL NOT NULL
                )
            """)

            conn.commit()

    # ─── INITIAL SEEDING ───────────────────────────────────────────────────────

    def _seed_if_empty(self):
        """Seeds SQLite tables from JSON data files when the tables are empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ── Minimal Pairs ────────────────────────────────────────────────
            cursor.execute("SELECT COUNT(*) FROM exercises_minimal_pairs")
            if cursor.fetchone()[0] == 0 and os.path.exists("data/minimal_pairs.json"):
                try:
                    with open("data/minimal_pairs.json", "r", encoding="utf-8") as f:
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
                    print(f"[DB] Seeded {len(items)} minimal pairs.")
                except Exception as e:
                    print(f"[DB] Error seeding minimal pairs: {e}")

            # ── Monosyllables ────────────────────────────────────────────────
            cursor.execute("SELECT COUNT(*) FROM exercises_monosyllables")
            if cursor.fetchone()[0] == 0 and os.path.exists("data/monosyllables.json"):
                try:
                    with open("data/monosyllables.json", "r", encoding="utf-8") as f:
                        items = json.load(f)
                    for idx, item in enumerate(items):
                        item_id = item.get("id") or f"mo_{idx+1}_{uuid.uuid4().hex[:4]}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO exercises_monosyllables
                                (id, word, category, source, difficulty)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            item_id,
                            item.get("word", ""),
                            item.get("category", "Einsilber"),
                            item.get("source", "Freiburger Einsilber-Test (DIN 45621)"),
                            item.get("difficulty", "Einfach"),
                        ))
                    print(f"[DB] Seeded {len(items)} monosyllables.")
                except Exception as e:
                    print(f"[DB] Error seeding monosyllables: {e}")

            # ── Numbers ──────────────────────────────────────────────────────
            cursor.execute("SELECT COUNT(*) FROM exercises_numbers")
            if cursor.fetchone()[0] == 0 and os.path.exists("data/numbers.json"):
                try:
                    with open("data/numbers.json", "r", encoding="utf-8") as f:
                        items = json.load(f)
                    for idx, item in enumerate(items):
                        item_id = item.get("id") or f"nu_{idx+1}_{uuid.uuid4().hex[:4]}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO exercises_numbers
                                (id, type, source, value, spoken, difficulty)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            item_id,
                            item.get("type") or item.get("category") or "Einfache Zahlen",
                            item.get("source", "Audiologischer Zahlen- & Uhrzeitentest"),
                            item.get("value", ""),
                            item.get("spoken", ""),
                            item.get("difficulty", "Einfach"),
                        ))
                    print(f"[DB] Seeded {len(items)} numbers.")
                except Exception as e:
                    print(f"[DB] Error seeding numbers: {e}")

            # ── Sentences ────────────────────────────────────────────────────
            cursor.execute("SELECT COUNT(*) FROM exercises_sentences")
            if cursor.fetchone()[0] == 0 and os.path.exists("data/sentences.json"):
                try:
                    with open("data/sentences.json", "r", encoding="utf-8") as f:
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
                    print(f"[DB] Seeded {len(items)} sentences.")
                except Exception as e:
                    print(f"[DB] Error seeding sentences: {e}")

            conn.commit()

    # ─── READ ALL EXERCISES ────────────────────────────────────────────────────

    def get_all_exercises(self) -> dict:
        """
        Returns all exercises from the database grouped by type.
        The structure is fully backwards-compatible with the old JSON-based API.
        """
        res = {
            "minimal_pairs": [],
            "monosyllables": [],
            "numbers": [],
            "sentences": [],
        }

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Minimal Pairs
            cursor.execute(
                "SELECT id, category, source, options_json, word_a, word_b, difficulty, hint"
                " FROM exercises_minimal_pairs"
            )
            for row in cursor.fetchall():
                item_id, cat, src, opts_j, wa, wb, diff, hint = row
                item: dict = {
                    "id": item_id,
                    "category": cat,
                    "source": src,
                    "difficulty": diff,
                    "hint": hint,
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

            # 2. Monosyllables
            cursor.execute(
                "SELECT id, word, category, source, difficulty FROM exercises_monosyllables"
            )
            for row in cursor.fetchall():
                item_id, word, cat, src, diff = row
                res["monosyllables"].append({
                    "id": item_id,
                    "word": word,
                    "category": cat,
                    "source": src,
                    "difficulty": diff,
                })

            # 3. Numbers
            cursor.execute(
                "SELECT id, type, source, value, spoken, difficulty FROM exercises_numbers"
            )
            for row in cursor.fetchall():
                item_id, num_type, src, val, spoken, diff = row
                res["numbers"].append({
                    "id": item_id,
                    # Expose both 'type' and 'category' for frontend compatibility
                    "type": num_type,
                    "category": num_type,
                    "source": src,
                    "value": val,
                    "spoken": spoken,
                    "difficulty": diff,
                })

            # 4. Sentences
            cursor.execute(
                "SELECT id, category, source, sentence, target_word, options_json, hint"
                " FROM exercises_sentences"
            )
            for row in cursor.fetchall():
                item_id, cat, src, sentence, target, opts_j, hint = row
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
                    "target_word": target,
                    "options": opts,
                    "hint": hint,
                })

        return res

    # ─── CREATE ───────────────────────────────────────────────────────────────

    def add_exercise(self, mod_type: str, item: dict) -> dict:
        """Inserts a new exercise into the corresponding table and returns it with its assigned ID."""
        item_id = item.get("id") or f"{mod_type[:2]}_{uuid.uuid4().hex[:6]}"
        item = dict(item)  # do not mutate caller's dict
        item["id"] = item_id

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

            elif mod_type == "monosyllables":
                cursor.execute("""
                    INSERT INTO exercises_monosyllables
                        (id, word, category, source, difficulty)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item_id,
                    item.get("word", ""),
                    item.get("category", "Einsilber"),
                    item.get("source", "Eigenes Übungsmaterial"),
                    item.get("difficulty", "Einfach"),
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

            elif mod_type == "monosyllables":
                cursor.execute("""
                    UPDATE exercises_monosyllables
                    SET word=?, category=?, source=?, difficulty=?
                    WHERE id=?
                """, (
                    item.get("word", ""),
                    item.get("category", "Einsilber"),
                    item.get("source", "Eigenes Übungsmaterial"),
                    item.get("difficulty", "Einfach"),
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
            "monosyllables": "exercises_monosyllables",
            "numbers": "exercises_numbers",
            "sentences": "exercises_sentences",
        }
        table_name = table_map.get(mod_type)
        if not table_name:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM training_logs")
            conn.commit()

    def get_summary_stats(self) -> dict:
        return self.get_stats()

    def get_stats(self) -> dict:
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

    def get_freiburger_test_lists(self) -> dict:
        """Returns monosyllable words grouped into official 20-word Freiburger Testlists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, word, category, source, difficulty FROM exercises_monosyllables ORDER BY id ASC")
            all_words = [{"id": r[0], "word": r[1], "category": r[2], "source": r[3], "difficulty": r[4]} for r in cursor.fetchall()]

        lists = {}
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

    def log_test_run(self, test_name: str, list_num: int, total_words: int, correct_words: int, score_percent: float):
        """Logs a completed Freiburger test run into database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO test_runs (timestamp, test_name, list_num, total_words, correct_words, score_percent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now, test_name, list_num, total_words, correct_words, score_percent))
            conn.commit()

    def get_test_runs(self) -> list:
        """Returns history of all completed test runs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, test_name, list_num, total_words, correct_words, score_percent
                FROM test_runs
                ORDER BY id DESC
            """)
            return [{
                "id": r[0],
                "timestamp": r[1],
                "test_name": r[2],
                "list_num": r[3],
                "total_words": r[4],
                "correct_words": r[5],
                "score_percent": r[6]
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



