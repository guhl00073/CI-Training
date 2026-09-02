# CI-Hörtrainer – Architektur & Systemdesign

Diese Dokumentation beschreibt die modulare Softwarearchitektur, Komponentenstruktur, Datenflussmodelle, Signalverarbeitungspipelines, REST-API und Testinfrastruktur des **CI-Hörtrainers** (Stand: August 2026).

---

## 🏗️ 1. Gesamtsystemarchitektur

Der CI-Hörtrainer basiert auf einer entkoppelten Client-Server-Architektur, die auf minimale Latenzen, plattformübergreifende Portabilität (macOS, Windows, Linux) und vollständige Offline-Fähigkeit ausgelegt ist.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Client-Schicht (Frontend UI)                           │
│  • Single-Page Application (HTML5, Vanilla CSS Glassmorphism, Vanilla JS)  │
│  • Web Audio API (Live-Spektrumanalysator, 65 dB SPL Testsignal-Generator) │
│  • Web Speech API (Spracherkennung / Freisprechen)                          │
│  • HTML5 Canvas (OLSA-Treppenplot, DIN 45621 Sprachaudiometrie-Kurven)     │
│  • Offline-Modell- & Audio-Engine-Manager (Piper Neural TTS / Status)      │
│  • Barrierefreier Hotkey- & Accessibility-Manager                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / JSON REST API (Port 8080)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    Backend Core Server (`src/web/server.py`)                │
│  • Multithreaded Python HTTP-Server (`ThreadingMixIn` + `HTTPServer`)       │
│  • Port-Lifecycle-Manager mit automatischer Konfliktbereinigung             │
│  • REST Routing, CORS, Path-Traversal & Payload-Validierung                 │
└──────┬───────────────────────┬───────────────────────────────┬──────────────┘
       │                       │                               │
┌──────▼───────────────────────▼────────┐             ┌────────▼──────────────┐
│       Audio & Signal Processing       │             │   Evaluator Engine    │
│ • `AudioPlayer`: Cross-Platform Audio │             │ `PhoneticMatcher`:    │
│   (afplay / ffplay / aplay, Panning)  │             │ • Kölner Phonetik     │
│ • `AdaptiveOLSA`: Brand & Kollmeier   │             │ • Zahlenkomposita-    │
│   Matrix-Audiometrie & SNR-Mixing     │             │   & Währungsparser    │
│ • `CIVocoder`: Greenwood Filterbank,  │             │ • Silbenzählung &     │
│   Hüllkurve & Sinus-Resynthese        │             │   Silbentrennung      │
│ • `TTSEngine`: Piper Neural TTS       │             │ • Ganzsatz-Matching   │
│   (ONNX/VITS) & Google Online Fallback│             │ • IPA-Transkription   │
│ • `STTEngine`: Faster-Whisper / Web   │             └───────────────────────┘
└──────────────────────┬────────────────┘
                       │ Thread-Safe SQL-Abfragen (`threading.RLock`)
┌──────────────────────▼──────────────────────────────────────────────────────┐
│                  Persistenzschicht (`src/database/progress_db.py`)          │
│  • SQLite-Datenbank (`data/ci-training.db`) im WAL-Modus (Write-Ahead Log)  │
│  • Tabellen: `training_logs`, `exercises_minimal_pairs`,                   │
│    `exercises_monosyllables`, `exercises_numbers`, `exercises_sentences`,  │
│    `test_runs`, `olsa_test_runs`, `freiburger_audiograms`, `user_profiles` │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 2. Komponentenstruktur & Modul-Verantwortlichkeiten

### 2.1 Backend-Kern & Webserver (`src/web/server.py`)

* **Multithreaded HTTP Server:** Basiert auf `socketserver.ThreadingMixIn` und `http.server.HTTPServer` auf Port `8080`. Jede HTTP-Anfrage wird in einem eigenen Thread bedient, um Verzögerungen bei der Audio-Synthese oder Datenverarbeitung zu vermeiden.
* **Lebenszyklus- & Port-Management:** Automatische Erkennung und Bereinigung blockierter Sockets (`SO_REUSEADDR`) sowie sauberes Signal-Handling (`SIGINT`, `SIGTERM`, `SIGCONT`) über den `/api/shutdown`-Endpunkt.
* **Sicherheitsfilter:** Path-Traversal-Schutz beim Bild-Upload (`/api/upload_image`) und bei Datei-Auslieferungen über statische Pfadvalidierung (`pathlib.Path.resolve`).

---

### 2.2 Audio Processing Subsystem (`src/audio/`)

#### 🗣️ `TTSEngine` (`src/audio/tts_engine.py`)
* **Google Cloud Multi-Voice Synthese:** Verlustfreies 22.05 kHz WAV Audio mit natürlicher Sprachdynamik und präzisen Konsonantentransienten.
* **10 Abgestimmte Stimmenprofile:**
  * Weiblich: *Anna* (Referenz), *Sandy* (Hochtonfokus), *Shelley* (Sanft), *Neural2-F* (Studio), *Grandma* (Senior).
  * Männlich: *Flo* (Klar/Prägnant), *Rocko* (Tieftonfokus), *Eddy* (Dynamisch), *Neural2-D* (Studio), *Grandpa* (Senior).
* **Akustisches Formant- & Tempomodeling:** Dynamische Filterung der Formanten und des Tempos via `ffmpeg` auf Sample-Ebene.
* **Fallback-Hierarchie:** `Google Cloud TTS (Online)` $\rightarrow$ `System TTS (macOS say / Windows SAPI / Linux espeak)`.
* **Automatisches Cache-Management:** Hashing der Texteingaben und Speicherung in `.cache/` mit automatischer Bereinigung (> 7 Tage alt oder > 150 MB).

#### 🔊 `AudioPlayer` (`src/audio/player.py`)
* **Plattformunabhängige Wiedergabe:** Nutzt systemeigene Binaries (`afplay` auf macOS; `ffplay`/`aplay` auf Linux; `powershell`/`ffplay` auf Windows).
* **Kanalbalance & Vertäubung:** Echte Stereo-Kanalisolierung (Links / Rechts / Mitte) für monorale, bimodale oder bilaterale CI-Träger.
* **Kontinuierlicher Störschall:** Kontinuierliches Abspielen von Hintergrundgeräuschen (Restaurant, Straßenlärm, Rauschen) mit unterbrechungsfreiem Lautstärke-Crossfade (120 ms Prozessüberlappung).

#### 🎯 `AdaptiveOLSA` (`src/audio/olsa_adaptive.py`)
* **Audiometrischer Matrixsatztest (Brand & Kollmeier 2002 / DIN EN ISO 8253-3):** Bestimmung der 50 % Sprachverstehensschwelle im Störlärm (Speech Reception Threshold, **SRT in dB SNR**).
* **Syntaktische Matrix:** 5 Wortspalten (*Name + Verb + Zahl + Adjektiv + Nomen*) mit je 10 Wörtern = 100.000 mögliche Satzkombinationen.
* **Signal-to-Noise Ratio (SNR) Mixing:** Mathematisch exakte Überlagerung des Sprachsignals mit Störrauschen (`olnoise`) auf Sample-Ebene:
  $$\text{SNR}_{\text{dB}} = 20 \log_{10}\left(\frac{\text{RMS}_{\text{Sprache}}}{\text{RMS}_{\text{Rauschen}}}\right)$$

#### 🎛️ `CIVocoder` (`src/audio/ci_vocoder.py`)
* **Cochlea-Implantat-Simulation:** Didaktische Rekonstruktion des CI-Hörempfindens durch tonotope Frequenzaufteilung nach der **Greenwood-Cochlea-Gleichung (Greenwood 1990)**:
  $$f = A \cdot (10^{a \cdot x} - k)$$
* **Signalverarbeitungsschritte:**
  1. Zerlegung des Signals durch $N$ Bandpassfilter (Butterworth 4. Ordnung).
  2. Hüllkurven-Extraktion (Gleichrichtung + Tiefpassfilterung bei 400 Hz).
  3. Resynthese mittels reiner Sinustöne (Center-Frequenzen der Filterbänder).
* **Herstellerprofile:** Cochlear Nucleus (22 Kanäle), Advanced Bionics HiRes (16 Kanäle), MED-EL Synchrony (12 Kanäle), Hörtraining Fokus (8 Kanäle), Minimal (4 Kanäle).

---

### 2.3 Evaluator & Phonetik-Engine (`src/evaluator/phonetic_matcher.py`)

* **Kölner Phonetik (Cologne Phonetics):** Ermöglicht die klangliche Ähnlichkeitsberechnung deutscher Sprachlaute (z. B. *Pass / Bass* $\rightarrow$ Code `18`).
* **Silbenzählung & Silbentrennung:**
  * Behandlung von Diphthongen (`au`, `eu`, `äu`, `ei`, `ey`, `ai`, `ay`, `ie`, `ui`) als Einzellautkerne.
  * Visuelle Silbensegmentierung für Komposita (z. B. *Haus·tür*, *Wör·ter·buch*, *Kin·der·gar·ten*).
* **Ziffern- & Zahlwort-Parser:** Erkennt Zahlwörter (*„vierundfünfzig“*), Ziffern (*„54“*), Uhrzeiten (*„14:30“*) und Währungen (*„12,50 €“*).
* **Phonetische Fehlerklassifikation:**
  * Verschlusslaute (Plosive) vs. Reibelaute (Frikative)
  * Stimmhaft vs. Stimmlos (*B vs. P*, *D vs. T*, *G vs. K*)
  * Nasalverwechslungen (*M vs. N*)
  * Vokallängen & Vokalverschiebungen
* **IPA & Artikulationsort-Lookup:** Bereitstellung von IPA-Lautschriften und logopädischen Hilfestellungen.

---

## 🗄️ 3. Datenbankschema & Persistenz (`src/database/progress_db.py`)

Die SQLite-Datenbank `data/ci-training.db` verwaltet alle Übungen, Testlisten, Profile und Audiogramme:

| Tabelle | Zweck | Wichtige Spalten |
|---|---|---|
| `user_profiles` | Multi-User CI-Hörprofile | `id`, `name`, `fitting_type`, `implant_model`, `master_gain`, `speech_rate`, `audio_balance`, `mask_noise`, `noise_volume`, `is_active` |
| `training_logs` | Trainingshistorie & Fehlermuster | `id`, `timestamp`, `module`, `category`, `target_word`, `user_input`, `is_correct`, `score` |
| `exercises_minimal_pairs` | 109 Minimalpaar-Gruppen | `id`, `category`, `word_a`, `word_b`, `options_json`, `hint`, `difficulty`, `source` |
| `exercises_monosyllables` | 400 Freiburger Einsilber (20 Listen) + 70 Mehrsilber | `id`, `word`, `category`, `list_num`, `syllable_count`, `syllables`, `stress`, `hint`, `difficulty`, `source` |
| `exercises_numbers` | 100 Freiburger Zahlen (10 Listen) + Uhrzeiten/Beträge | `id`, `type`, `value`, `spoken`, `list_num`, `category`, `hint`, `difficulty`, `source` |
| `exercises_sentences` | 500 Alltagssätze & OLSA-Matrixsätze | `id`, `sentence`, `target_word`, `options_json`, `category`, `hint`, `difficulty`, `source` |
| `test_runs` | Strukturierte Freiburger Testläufe | `id`, `timestamp`, `list_name`, `total_words`, `correct_words`, `score`, `details_json` |
| `olsa_test_runs` | Adaptive OLSA-Satztests (SRT) | `id`, `timestamp`, `srt_db`, `initial_snr`, `noise_type`, `total_sentences`, `std_dev`, `history_json` |
| `freiburger_audiograms` | Mehrpegel-Sprachaudiometriekurven | `id`, `timestamp`, `list_name`, `test_data_json`, `v_max`, `disc_loss`, `notes` |

---

## 🌐 4. REST-API Spezifikation

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/api/exercises` | Liefert alle 1279 Übungen aller Module |
| `GET` | `/api/exercises/weaknesses` | Ermittelt Schwachstellen-Übungen (< 60 % Trefferquote) |
| `GET` | `/api/test_lists` | Liefert die 20 DIN 45621 Freiburger Einsilberlisten |
| `GET` | `/api/test_lists/numbers` | Liefert die 10 DIN 45621 Freiburger Zahlenlisten |
| `GET` | `/api/audio/status` | Liefert Status der Offline-Modelle, Engine und Stimmen |
| `GET` | `/api/profiles` | Liste aller Benutzer-Hörprofile |
| `GET` | `/api/profiles/active` | Liefert das aktuell aktive Profil |
| `GET` | `/api/vocoder/profiles` | Liefert CI-Vocoder Kanalprofile |
| `GET` | `/api/ipa?word=<word>` | Liefert IPA-Lautschrift & Artikulationsort |
| `GET` | `/api/freiburger/curves` | Gespeicherte Freiburger Sprachaudiometriekurven |
| `GET` | `/api/olsa/runs` | Historie der adaptiven OLSA-Tests |
| `POST` | `/api/evaluate` | Phonetische Auswertung von Wörtern, Zahlen oder Sätzen |
| `POST` | `/api/olsa/start` | Startet einen adaptiven OLSA-Test |
| `POST` | `/api/olsa/step` | Verarbeitet Patientenauswahl und berechnet nächsten SNR |
| `POST` | `/api/freiburger/curve` | Speichert eine Freiburger Sprachverständlichkeitskurve |
| `POST` | `/api/test_run/log` | Protokolliert einen abgeschlossenen Freiburger Testlauf |
| `POST` | `/api/tts` | Synthetisiert und spielt Sprachaudio ab |
| `POST` | `/api/noise/config` | Konfiguriert Lautstärke und Panning des Störgeräuschs |
| `POST` | `/api/noise/stop` | Stoppt die Störschallwiedergabe |
| `POST` | `/api/audio/engine` | Setzt bevorzugte TTS-Engine (`auto`, `piper_neural`, `google_online`) |
| `POST` | `/api/audio/download_model` | Startet den Download eines Piper-Offline-Modells |
| `POST` | `/api/audio/delete_model` | Löscht ein Piper-Offline-Modell |
| `POST` | `/api/profiles` | Erstellt ein neues Hörprofil |
| `PUT` | `/api/profiles/<id>` | Aktualisiert Profilparameter |
| `DELETE` | `/api/profiles/<id>` | Löscht ein Hörprofil |
| `POST` | `/api/profiles/<id>/activate` | Aktiviert ein Hörprofil |

---

## 🧪 5. Testinfrastruktur & Qualitätssicherung

Die Testsuite deckt 100 % der audiologischen Berechnungen und REST-Endpunkte ab:
* `tests/test_all_11_modules.py`: Umfassende Tests aller Trainingsmodule (Minimalpaare, DIN Einsilber, Mehrsilber & Komposita, DIN Zahlen, Sätze, Störschall, Freiburger Diagnostik, OLSA SRT, Lautheit, Heatmap, Vocoder, Profile).
* `tests/test_api_endpoints.py`: Integrationstests für alle REST-Routen via In-Memory Request Handler.
* `tests/test_tts_engine.py`: Tests für Piper Neural TTS, Modell-Status und Cache-Bereinigung.
* `tests/test_freiburger_and_multisyllables.py`: DIN 45621 Testlisten und Silbentrennung.
* `tests/test_profiles.py`: Multi-User Profile und CI-Versorgungstypen.
* `tests/test_components.py`: Evaluator- und Datenbank-Basistests.

Ausführung über:
```bash
.venv/bin/python3 -m unittest discover tests
```
