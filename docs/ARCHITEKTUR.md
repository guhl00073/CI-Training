# CI-Hörtrainer – Architektur & Systemdesign

Diese Dokumentation beschreibt die modulare Architektur der CI-Hörtrainer-Anwendung.

---

## 🏗️ Systemübersicht

```
┌─────────────────────────────────────────────────────────────┐
│                    Benutzeroberflächen                       │
│     Web Application (HTML5 / JS)  │  Desktop App (Tkinter)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST API / Python Imports
┌──────────────────────────────▼──────────────────────────────┐
│                    Backend Core Engine                      │
│   src/web/server.py  │  src/audio/player.py  │  src/audio/  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                 Datenbank & Auswertung                      │
│   data/ci-training.db (SQLite)  │  PhoneticMatcher Engine   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Komponentenstruktur

- **`src/audio/player.py` (`AudioPlayer`):**
  - Cross-Plattform Audio-Player (macOS `afplay`, Windows/Linux `ffplay`/`aplay`).
  - Unterstützt Stereo-Panning (Gegenlaterale Vertäubung), kontinuierlichen Störschall (Restaurant, Traffic, Station) und synchrone/asynchrone Sprachwiedergabe (`wait_until_done`).

- **`src/audio/tts_engine.py` (`TTSEngine`):**
  - Hybride Sprachsynthese mit automatischem Fallback:
    1. Online Google Neural TTS (hohe Sprachqualität).
    2. Native macOS-Stimmen (`say -v Anna` etc.) für Offline-Nutzung.
  - Caching-System in `.cache/` zur Minimierung von Netzwerkanfragen.

- **`src/database/progress_db.py` (`ProgressDatabase`):**
  - SQLite-Datenbankmanager für `data/ci-training.db`.
  - Verwaltet Aufzeichnungen aller Übungsversuche, XP-Punkte, Level-Fortschritt und Übungskataloge.

- **`src/evaluator/phonetic_matcher.py` (`PhoneticMatcher`):**
  - Phonetischer Evaluator zur Analyse von Wortabweichungen (Anlaut, Vokal, Auslaut).
  - Spezielle Regelwerke für Zahlen-, Zeit- und Währungsformate.

- **`src/web/server.py` & `src/web/static/`:**
  - Leichtgewichtiger Python-HTTP-Server auf Port 8080.
  - Responsive Web-Interface mit Glassmorphism-Design, Audio-Visualizer und Barrierefreiheit.

---

## 🗄️ Datenbank-Schema (`data/ci-training.db`)

1. **`exercises_minimal_pairs`**: Minimalpaar-Katalog (109 Eintragsgruppen).
2. **`exercises_monosyllables`**: Freiburger Einsilber (235 Wörter).
3. **`exercises_numbers`**: Zahlen, Uhrzeiten und Beträge (100 Aufgaben).
4. **`exercises_sentences`**: Satzübungen (500 Sätze).
5. **`attempt_logs`**: Pro Protokollierung von Übungsversuchen mit Trefferquote und Modul.
