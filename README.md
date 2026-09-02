# CI-Hörtrainer (Auditory Training System für CI-Träger)

Eine spezialisierte Python-Anwendung mit moderner Web-Oberfläche für das audio-phonetische Hörtraining von Cochlea-Implantat (CI) Trägern.

---

## 🚀 Schnellstart

### macOS & Linux

```bash
./start_ci_trainer.sh
```
oder auf macOS einfach doppelklicken auf `start_ci_trainer.command`.

### Windows

Doppelklick auf `start_ci_trainer.bat`.

> **Automatische Einrichtung:** Das Startskript prüft automatisch, ob Python, eine virtuelle Umgebung (`.venv`) und die erforderlichen Pakete ([requirements.txt](file:///Users/gerald/Development/CI-Training/requirements.txt)) installiert sind. Fehlt Python, wird es automatisch über **Homebrew** (macOS/Linux) bzw. **winget** (Windows) installiert.

---

## 👂 Features & Die 11 Übungs- und Analysemodule

1. **🎭 Minimalpaar-Training**:
   - Unterscheidung phonetisch ähnlicher Wortpaare (*Pass / Bass*, *Tasse / Dasse*, *Kamm / Gramm*, *Rinne / Ringe*).
   - Auswertung über den **Kölner Phonetik Algorithmus** und detailliertes Konsonanten- & Vokal-Feedback.

2. **🔤 Einsilber-Training**:
   - Orientiert am **Freiburger Einsilber-Test** (DIN 45621) mit automatischer Analyse von Anlaut, Vokal und Auslaut sowie Spracheingabe per Mikrofon.

3. **🔢 Zahlen-, Uhrzeiten- & Betragsverständnis**:
   - Hörtraining für Einzelzahlen, mehrstellige Zahlen, Uhrzeiten (*14:30 Uhr*) und Geldbeträge (*12,50 €*).

4. **💬 Satzverständnis**:
   - **Wort-Fokus (Multiple Choice)** & **Ganzsatz-Diktat (Freitext / Spracheingabe)** mit wortweiser Bewertung.

5. **🎯 OLSA Adaptiver Satztest (Brand & Kollmeier 2002)**:
   - Audiometrischer 5-Wort-Matrixsatztest zur Bestimmung der 50 % Sprachverstehensschwelle im Störlärm (**SRT in dB SNR**) mit interaktivem Canvas-Treppenplot.

6. **🌊 Störschall-Training**:
   - Hören unter erschwerten Alltagsbedingungen (Café, Verkehr) mit standardisierten **SNR-Stufen in dB** (+10 dB bis -5 dB) und unterbrechungsfreiem Audio-Crossfade.

7. **🧠 Auditiv. Gedächtnis**:
   - Merkspannen-Training für Sequenzen aus 2 bis 6 Wörtern mit gesicherter Kartensperre während des Vorlesens.

8. **🎯 Adaptives Schwachstellen-Training**:
   - Automatisches Auslesen fehlerintensiver Phonem-Kategorien (< 60 % Trefferquote) aus der Historie.

9. **📈 Freiburger DIN-Audiogramm (DIN 45621)**:
   - Mehrpegel-Sprachaudiometrie (50 dB, 65 dB, 80 dB) mit Normalhörenden-Referenzkurve, $V_{\max}$ und Diskriminationsverlust.

10. **📊 Statistik & Heatmap**:
    - Phonem-Heatmap, XP-Level-Fortschritt, Reaktionszeiten und filterbare Protokolltabelle.

11. **✏️ Übungs-Editor & Kategoriemanager**:
    - Erstellung und Verwaltung eigener Übungen, Bulk-Import und globaler Kategoriemanager.

---

## 🎛️ Audiometrische Werkzeuge, Stimmen & Barrierefreiheit

* **🌐 Bilingual Hörtraining & Englische Sprachübungen (ESL)**: Umschalter `🇩🇪 DE` | `🇬🇧 EN` im App-Header für zweisprachiges Hörtraining von CI-Trägern mit Deutsch als Erstsprache. Enthält **146 kuratierte englische Übungseinheiten (182 Zielwörter/Sätze)** (36 Minimalpaare für Deutsch-Englisch Phonetikkontraste wie `/r/-/l/`, `th`/`/f/`/`/t/`, `/v/-/w/` & Vokallängen, 36 klinische CNC/NU-6 Einsilber, 30 Spondee-Mehrsilber, 24 Zahlen/Uhrzeiten/Beträge und 20 Alltags- & Matrixsätze) mit Microsoft Azure Neural (US/UK) und Double Metaphone Phonetikauswertung.
* **🌐 Microsoft Azure Neural & System-Stimmen:** 10 authentische 48-kHz-Studio-Sprecher (*Conrad, Florian, Killian, Katja, Amala, Seraphina, Jonas-AT, Ingrid-AT, Jan-CH, Leni-CH*) sowie US/UK Englisch Sprecher (*Ava, Andrew, Sonia, Ryan*) und dynamisch erkannte Mac/Windows-Systemstimmen (*Anna, Markus, Petra, Samantha, Alex*) mit Vorhörfunktion (`🔊 Stimme testen`).
* **🎙️ Intelligente Auto-Mic Spracherkennung:** Silbengenaue Vorlesezeitschätzung und automatische Mikrofonaktivierung für Freisprech-Training in allen Wort- und Satzmodulen.
* **👤 Multi-User Profilverwaltung:** Verwaltung seitengetrennter CI-Versorgungen (*Monoral L/R, Bilateral, Bimodal, SSD*) und Soundprozessoren (*Cochlear, MED-EL, Advanced Bionics, Oticon*) mit automatischer Echtzeit-Synchronisation aller Audioeinstellungen.
* **🔊 65 dB SPL Lautstärke-Kalibrierungs-Assistent:** Kalibrierung für Lautsprecher (Freifeld), Kopfhörer und Direct-Streaming via CCITT-Sprachrauschen und 1 kHz Sinuston.
* **🎛️ CI-Vocoder Simulation:** Greenwood (1990) Cochlea-Filterbank (4 bis 22 Kanäle) zur didaktischen Simulation des CI-Hörempfindens.
* **⌨️ Barrierefreie Tastatur-Hotkeys:** Vollständige Steuerung ohne Maus über Hotkeys (<kbd>Leertaste</kbd>/<kbd>P</kbd>, <kbd>1..6</kbd>, <kbd>Alt+1..9</kbd>, <kbd>Alt+O</kbd>, <kbd>Alt+A</kbd>, <kbd>Alt+P</kbd>/<kbd>U</kbd>, <kbd>H</kbd>/<kbd>?</kbd>).

---

## 📚 Ausführliche Dokumentation

* 📖 **[Benutzerhandbuch (USER_GUIDE.md)](docs/USER_GUIDE.md)**: Detaillierte Anleitung aller Module, Profilverwaltung, Kalibrierung und audiologische Praxistipps.
* 🏗️ **[Architektur & Systemdesign (ARCHITEKTUR.md)](docs/ARCHITEKTUR.md)**: Systemarchitektur, Modulstruktur, REST-API-Spezifikation, Datenbank-Schema und Signalverarbeitung.
* 🚀 **[Release Notes (RELEASE_NOTES.md)](docs/RELEASE_NOTES.md)**: Detaillierte Versionshistorie und Änderungsprotokolle.

---

## 🧪 Tests ausführen

```bash
python3 -m unittest discover tests
```
