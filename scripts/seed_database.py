#!/usr/bin/env python3
"""
seed_database.py
────────────────
Initialisiert oder re-initialisiert die SQLite-Datenbank (data/ci-training.db)
aus den JSON-Quelldateien in data/*.json.

Verwendung:
    python3 scripts/seed_database.py           # Normaler Seed (nur wenn Tabellen leer)
    python3 scripts/seed_database.py --force   # Bestehende Daten überschreiben
"""

import sys
import os
import json
import sqlite3
import uuid
import pathlib
import argparse

# ─── Pfad-Setup ───────────────────────────────────────────────────────────────
from src.utils.paths import get_resource_path, get_db_path

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DB_PATH = get_db_path()
DATA_DIR = get_resource_path("data")

JSON_FILES = {
    "minimal_pairs":  DATA_DIR / "minimal_pairs.json",
    "monosyllables":  DATA_DIR / "monosyllables.json",
    "multisyllables": DATA_DIR / "multisyllables.json",
    "numbers":        DATA_DIR / "numbers.json",
    "sentences":      DATA_DIR / "sentences.json",
}

TABLES = {
    "minimal_pairs": "exercises_minimal_pairs",
    "monosyllables": "exercises_words",
    "multisyllables": "exercises_words",
    "words":         "exercises_words",
    "numbers":       "exercises_numbers",
    "sentences":     "exercises_sentences",
}


def load_json(path: pathlib.Path) -> list:
    if not path.exists():
        print(f"  ⚠️  JSON-Datei nicht gefunden: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_minimal_pairs(cursor, items: list, force: bool):
    if force:
        cursor.execute("DELETE FROM exercises_minimal_pairs WHERE source LIKE '%Marburger%' OR id LIKE 'mp_%'")
    for idx, item in enumerate(items):
        item_id = item.get("id") or f"mp_{idx+1}_{uuid.uuid4().hex[:4]}"
        opts = item.get("options")
        opts_j = json.dumps(opts, ensure_ascii=False) if opts is not None else None
        cursor.execute("""
            INSERT OR REPLACE INTO exercises_minimal_pairs (id, category, source, options_json, word_a, word_b, difficulty, hint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            item.get("category", "Allgemein"),
            item.get("source", "Marburger Minimalpaar-Katalog"),
            opts_j,
            item.get("word_a"),
            item.get("word_b"),
            item.get("difficulty", "Mittel"),
            item.get("hint")
        ))
    return len(items)


def seed_monosyllables(cursor, items: list, force: bool):
    if force:
        cursor.execute("DELETE FROM exercises_words WHERE source LIKE '%Freiburger%' OR id LIKE 'mo_%' OR id LIKE 'es_%'")
    for idx, item in enumerate(items):
        item_id = item.get("id") or f"mo_{idx+1}_{uuid.uuid4().hex[:4]}"
        cursor.execute("""
            INSERT OR REPLACE INTO exercises_words (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint)
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
    return len(items)


def seed_multisyllables(cursor, items: list, force: bool):
    if force:
        cursor.execute("DELETE FROM exercises_words WHERE source LIKE '%Mehrsilber%' OR id LIKE 'ms_%'")
    for idx, item in enumerate(items):
        item_id = item.get("id") or f"ms_{idx+1}_{uuid.uuid4().hex[:4]}"
        cursor.execute("""
            INSERT OR REPLACE INTO exercises_words (id, word, category, source, difficulty, list_num, syllables, syllable_count, stress, hint)
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
    return len(items)


def seed_numbers(cursor, items: list, force: bool):
    if force:
        cursor.execute("DELETE FROM exercises_numbers")
    for idx, item in enumerate(items):
        item_id = item.get("id") or f"nu_{idx+1}_{uuid.uuid4().hex[:4]}"
        cursor.execute("""
            INSERT OR REPLACE INTO exercises_numbers (id, type, source, value, spoken, difficulty, list_num)
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
    return len(items)


def seed_sentences(cursor, items: list, force: bool):
    if force:
        cursor.execute("DELETE FROM exercises_sentences")
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
    return len(items)


def main():
    parser = argparse.ArgumentParser(description="Seed CI-Hörtrainer SQLite-Datenbank aus JSON-Dateien.")
    parser.add_argument("--force", action="store_true",
                        help="Bestehende Übungsdaten loeschen und neu einlesen (Fortschrittslogs bleiben erhalten).")
    parser.add_argument("--db", default=str(DB_PATH),
                        help=f"Pfad zur SQLite-Datenbank (Standard: {DB_PATH})")
    args = parser.parse_args()

    db_path = pathlib.Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"  CI-Hoertrainer - Datenbank-Seed")
    print(f"{'='*55}")
    print(f"  Datenbank : {db_path}")
    print(f"  Modus     : {'--force (Ueberschreiben)' if args.force else 'Normal (nur wenn leer)'}")
    print()

    # Sicherstellen dass Tabellen existieren (via ProgressDatabase.__init__)
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(str(PROJECT_ROOT))

    from src.database.progress_db import ProgressDatabase
    # Instantiate just to run _init_db(); _seed_if_empty() wird danach
    # manuell mit Force-Option gesteuert
    db_obj = ProgressDatabase(str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    seeders = {
        "minimal_pairs": seed_minimal_pairs,
        "monosyllables": seed_monosyllables,
        "multisyllables": seed_multisyllables,
        "numbers":       seed_numbers,
        "sentences":     seed_sentences,
    }

    tables_map = {
        "minimal_pairs": "exercises_minimal_pairs",
        "monosyllables": "exercises_words",
        "multisyllables": "exercises_words",
        "numbers":       "exercises_numbers",
        "sentences":     "exercises_sentences",
    }

    total = 0
    for key, seeder_fn in seeders.items():
        table = tables_map[key]
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count_before = cursor.fetchone()[0]

        if count_before > 0 and not args.force and key not in ("multisyllables", "monosyllables", "numbers"):
            print(f"  skip  {table:<35} bereits befüllt ({count_before} Eintraege)")
            continue

        items = load_json(JSON_FILES[key])
        if not items:
            continue

        n = seeder_fn(cursor, items, args.force)
        conn.commit()

        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count_after = cursor.fetchone()[0]
        symbol = "+" if not args.force else "reset"
        print(f"  OK    {table:<35} {count_after} Eintraege ({symbol} {n})")
        total += n

    conn.close()
    print()
    if total == 0:
        print("  Datenbank war bereits vollstaendig befuellt. Nichts geaendert.")
        print("  Nutze --force um alle Uebungen neu einzulesen.")
    else:
        print(f"  Seed abgeschlossen - {total} Datensaetze verarbeitet.")
    print()


if __name__ == "__main__":
    main()
