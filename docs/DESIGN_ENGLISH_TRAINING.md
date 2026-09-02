# Technical Design: English Vocabulary, Voices & Phonetics for CI Trainer

## 1. Overview & Purpose
This document details the validated architecture and technical specifications for expanding **CI Trainer (CI-Hörtrainer)** to support **English Vocabulary, English Azure/System Voices, Speech-to-Text Recognition, and Phonetic Analysis**.

This feature enables German-speaking Cochlear Implant (CI) wearers to train their auditory comprehension of English as a second language using standardized clinical word lists and tailored audiological feedback.

---

## 2. Documented Scope & Assumptions

### Target Audience & UX Scope
* **Target Audience**: German native speakers with Cochlear Implants training English auditory skills.
* **UI Localization**: Navigation, buttons, menus, and audiological feedback tips remain in German. Exercise content and speech audio switch to English.
* **Translation Hints**: German translations are available on demand via a `Tipp / Übersetzung` hint button.

### Voice & Recognition Constraints
* **Voice Accents**: US English (`en-US`) and UK English (`en-GB`).
* **TTS Voices**: Microsoft Azure Neural Studio voices (`en-US-AvaNeural`, `en-US-AndrewNeural`, `en-GB-SoniaNeural`, `en-GB-RyanNeural`) + Native OS system voices (`Samantha`, `Alex`, `Daniel`, `Zira`, `David`).
* **STT Recognition**: Google Speech Recognition API with `language="en-US"` / `"en-GB"`.
* **Connectivity Requirement**: Active internet connection required for English Neural TTS and STT recognition.

---

## 3. System Architecture & Components

```
[Header Language Switcher 🇩🇪 DE / 🇬🇧 EN]
              │
              ▼ (activeLanguage: "de" | "en")
[REST API Server: /api/exercises/*?lang=en]
     │              │               │
     ▼              ▼               ▼
[TTS Engine]   [STT Engine]   [Phonetic Evaluator]
(Azure/System) (Google ASR)   (DE: Cologne / EN: Double Metaphone)
```

### A. Database Schema & Datasets (`progress_db.py` & `data/`)
* **Schema Migration**: Add `language TEXT DEFAULT 'de'` and `translation_de TEXT` to exercise tables (`exercises_minimal_pairs`, `exercises_words`, `exercises_sentences`, `exercises_numbers`).
* **English Exercise Datasets**:
  * `data/minimal_pairs_en.json`: Contrastive English word pairs (*rake/lake*, *think/sink*, *ship/sheep*, *pat/bat*).
  * `data/monosyllables_en.json`: Standardized CNC / NU-6 monosyllables (*check, note, park, white, wide, youth, goose*).
  * `data/multisyllables_en.json`: Two-syllable equal-stress Spondee words (*cowboy, hotdog, baseball, ice cream, playground, pancake*).
  * `data/numbers_en.json` & `data/sentences_en.json`: Numbers, currency, time formats, and everyday conversation sentences.

### B. Audio TTS Engine (`src/audio/tts_engine.py`)
* Dynamic voice list filtering according to selected language (`de` vs `en`).
* Integration of Azure Neural English voices (`en-US-AvaNeural`, `en-GB-SoniaNeural`, etc.) and macOS/Windows system voices.

### C. Speech-to-Text Engine (`src/stt/stt_engine.py`)
* Dynamic language selection in `transcribe_wav(wav_file, language="en-US")`.

### D. Phonetic Evaluator (`src/evaluator/phonetic_matcher.py`)
* Route `evaluate(target, user_input, language)`:
  * `language == 'de'`: Kölner Phonetik.
  * `language == 'en'`: **Double Metaphone** + German-English Transfer Error Rules.
* **Specialized Audiological Error Classification for German Learners**:
  * **Liquid Contrast**: `/r/` vs `/l/` (*rake* vs *lake*).
  * **Dental Fricatives**: `/θ/` vs `/f/` / `/t/` (*think* vs *fink* / *tree*).
  * **Labiodental / Semivowel**: `/v/` vs `/w/` (*vine* vs *wine*).
  * **Vowel Length & Quality**: `/ɪ/` vs `/iː/` (*ship* vs *sheep*), `/æ/` vs `/ʌ/` (*cat* vs *cut*).

### E. Web Interface (`src/web/static/`)
* Language toggle button in top navbar (`🇩🇪 DE` | `🇬🇧/🇺🇸 EN`).
* Dynamic reload of exercise categories and voice options on language change.
* On-demand `💡 Tipp / Übersetzung` button to reveal German word translations.

---

## 4. Decision Log

| Decision | Choice Made | Alternatives Considered | Rationale |
| :--- | :--- | :--- | :--- |
| **Architecture** | Unified Multi-Language System | Isolated English Studio Tab, Category Tags | Maximum code reuse, scalable architecture, zero impact on existing German code. |
| **Target Group & UI** | German CI wearers (German UI labels & tips) | Full English UI localization | Users are German native speakers; German UI text and tips optimize learning UX. |
| **Voice Scope** | Azure Neural + OS System (`en-US`, `en-GB`) | US-only or 4+ global accents | Covers essential global English accents cleanly. |
| **Vocabulary Strategy** | Clinical CNC/NU-6 + Spondees + Minimal Pairs | Everyday A1 only or Business English | Aligns with standard clinical audiometric practices. |
| **Translation Hints** | On-demand button (`Tipp / Übersetzung`) | Always visible / Never visible | Prevents spoiling listening practice while giving optional support. |
| **Connectivity Requirement** | Internet connection required for English TTS/STT | Offline local fallback | Guarantees 48 kHz studio neural voice synthesis quality and ASR accuracy. |
