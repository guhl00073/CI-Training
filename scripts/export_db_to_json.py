#!/usr/bin/env python3
"""
export_db_to_json.py
────────────────────
Exportiert die Übungsdatenbank (data/ci-training.db) in synchrone JSON-Dateien im Ordner data/.
"""

import sqlite3
import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "ci-training.db"
DATA_DIR = PROJECT_ROOT / "data"


def export_minimal_pairs(cursor):
    cursor.execute("SELECT id, category, source, options_json, word_a, word_b, difficulty, hint FROM exercises_minimal_pairs")
    rows = cursor.fetchall()
    items = []
    for r in rows:
        opts = json.loads(r[3]) if r[3] else None
        item = {
            "id": r[0],
            "category": r[1],
            "source": r[2],
            "options": opts,
            "word_a": r[4],
            "word_b": r[5],
            "difficulty": r[6],
            "hint": r[7]
        }
        items.append(item)
    
    out_path = DATA_DIR / "minimal_pairs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Exportiert: {out_path} ({len(items)} Einträge)")


def export_monosyllables(cursor):
    cursor.execute("SELECT id, word, category, source, difficulty FROM exercises_monosyllables")
    rows = cursor.fetchall()
    items = []
    for r in rows:
        item = {
            "id": r[0],
            "word": r[1],
            "category": r[2],
            "source": r[3],
            "difficulty": r[4]
        }
        items.append(item)
    
    out_path = DATA_DIR / "monosyllables.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Exportiert: {out_path} ({len(items)} Einträge)")


def export_numbers(cursor):
    cursor.execute("SELECT id, type, source, value, spoken, difficulty FROM exercises_numbers")
    rows = cursor.fetchall()
    items = []
    for r in rows:
        item = {
            "id": r[0],
            "type": r[1],
            "source": r[2],
            "value": r[3],
            "spoken": r[4],
            "difficulty": r[5]
        }
        items.append(item)
    
    out_path = DATA_DIR / "numbers.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Exportiert: {out_path} ({len(items)} Einträge)")


def export_sentences(cursor):
    cursor.execute("SELECT id, category, source, sentence, target_word, options_json, hint FROM exercises_sentences")
    rows = cursor.fetchall()
    items = []
    for r in rows:
        opts = json.loads(r[5]) if r[5] else []
        item = {
            "id": r[0],
            "category": r[1],
            "source": r[2],
            "sentence": r[3],
            "target_word": r[4],
            "options": opts,
            "hint": r[6]
        }
        items.append(item)
    
    out_path = DATA_DIR / "sentences.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Exportiert: {out_path} ({len(items)} Einträge)")


def main():
    if not DB_PATH.exists():
        print(f"Fehler: Datenbank {DB_PATH} existiert nicht.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("Exportiere Datenbank-Übungen nach JSON...")
    export_minimal_pairs(cursor)
    export_monosyllables(cursor)
    export_numbers(cursor)
    export_sentences(cursor)

    conn.close()
    print("Export erfolgreich abgeschlossen!")


if __name__ == "__main__":
    main()
