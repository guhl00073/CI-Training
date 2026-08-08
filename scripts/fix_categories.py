#!/usr/bin/env python3
"""Setzt bei allen Freiburger-Einsilber-Test Eintraegen category = 'Einsilber'."""
import json, os

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monosyllables.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

fixed = 0
for entry in data:
    if "Freiburger" in entry.get("source", ""):
        if entry.get("category") != "Einsilber":
            entry["category"] = "Einsilber"
            fixed += 1

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Fertig: {fixed} Eintraege korrigiert. Gesamt: {len(data)} Eintraege.")
