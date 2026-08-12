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
  - Unterstützt Stereo-Panning (Gegenlaterale Vertäubung), kontinuierlichen Störschall (Café/Restaurant, Traffic) mit **unterbrechungsfreiem Lautstärke-Crossfade** (120ms Prozessüberlappung) und synchrone/asynchrone Sprachwiedergabe.

- **`src/audio/tts_engine.py` (`TTSEngine`):**
  - Hybride Sprachsynthese mit automatischem Fallback:
    1. Online Google Neural TTS (hohe Sprachqualität).
    2. Native macOS-Stimmen (`say -v Anna` etc.) für Offline-Nutzung.
  - Caching-System in `.cache/` mit **automatischem Cleanup-Mechanismus** (>7 Tage alt / >100 MB Gesamtgröße).

- **`src/database/progress_db.py` (`ProgressDatabase`):**
  - SQLite-Datenbankmanager für `data/ci-training.db` mit aktiviertem **Write-Ahead Logging (WAL-Modus)** für hohe Nebenläufigkeit.
  - Verwaltet Aufzeichnungen aller Übungsversuche, XP-Punkte, Level-Fortschritt, Übungskataloge und **Schwachstellen-Analysen** (`get_weak_exercises()`).

- **`src/evaluator/phonetic_matcher.py` (`PhoneticMatcher`):**
  - Phonetischer Evaluator zur Analyse von Wortabweichungen (Anlaut, Vokal, Auslaut).
  - Spezielle Regelwerke für Zahlen-, Zeit- und Währungsformate sowie **Ganzsatz-Evaluation** (`evaluate_full_sentence`) mit wortweisem Status und Trefferquote.

- **`src/web/server.py` & `src/web/static/`:**
  - Multithreaded Python-HTTP-Server (`ThreadingMixIn` + `HTTPServer`) auf Port 8080.
  - REST-API Endpunkte für Evaluierung (`/api/evaluate`), Schwachstellen (`/api/weaknesses`), Rauschsynchronisation (`/api/noise/config`) und Katalog-Verwaltung.
  - Responsive Web-Interface mit Glassmorphism-Design, Audio-Visualizer, Spracheingabe (Web Speech API) und Barrierefreiheit.

---

## 🗄️ Datenbank-Schema (`data/ci-training.db`)

1. **`exercises_minimal_pairs`**: Minimalpaar-Katalog (109 Eintragsgruppen).
2. **`exercises_monosyllables`**: Freiburger Einsilber (235 Wörter).
3. **`exercises_numbers`**: Zahlen, Uhrzeiten und Beträge (100 Aufgaben).
4. **`exercises_sentences`**: Satzübungen (500 Sätze).
5. **`attempt_logs`**: Protokollierung aller Übungsversuche mit Trefferquote, Fehlerkategorie und Modul für die Schwachstellen-Analyse.
