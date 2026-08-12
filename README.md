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

## 👂 Features & Übungsmodule

1. **Minimalpaar-Training**:
   - Unterscheidung phonetisch ähnlicher Wortpaare (z.B. *Pass / Bass*, *Tasse / Dasse*, *Haus / Maus*, *Kamm / Komm*).
   - Auswertung über den **Kölner Phonetik Algorithmus** und detailliertes Konsonanten- & Vokal-Feedback.

2. **Einsilber-Training**:
   - Orientiert am **Freiburger Einsilber-Test** (DIN 45621) (z.B. *Bus*, *Dach*, *Fisch*, *Brot*, *Strand*, *Herbst*).
   - Phonetisches Feedback mit automatischer Analyse von Anlaut, Vokal und Auslaut sowie optionaler Spracheingabe (Nachsprechen).

3. **Zahlen-, Uhrzeiten- & Betragsverständnis**:
   - Hörtraining für Einzelzahlen, zweistellige/dreistellige Zahlen, Uhrzeiten (z. B. *14:30 Uhr*) und Geldbeträge (z. B. *12,50 €*).

4. **Alltagssätze (Oldenburger Satztest / OLSA)**:
   - **Wort-Fokus (Multiple Choice)**: Höre den Satz und wähle das gesuchte Schlüsselwort.
   - **Ganzsatz-Diktat (Freie Eingabe & Spracheingabe)**: Höre den ganzen Satz (Text ausgeblendet) und tippe ihn ein oder sprich ihn nach. Wortweise Auswertung mit farblichen Wort-Badges (Grün/Rot) und Trefferquote (%).

5. **🎯 Adaptives Schwachstellen-Training**:
   - Automatisches Auslesen fehlerintensiver Phonem-Kategorien (< 60% Trefferquote) aus der Historie.
   - Generiert gezielte Übungs-Sets mit audiologischen Hinweisen, Satz-Maskierung (`"_______"`) und Autostart.

6. **CI-spezifische Audio-Steuerung & Adaptive SNR**:
   - **Stereo-Balance / Kanalisolierung**: Getrennte Ansteuerung des linken oder rechten Ohrs.
   - **Vertäubung & Störschall**: Zuschaltbares kontinuierliches Rauschen (Café/Restaurant, Straßenverkehr) mit **unterbrechungsfreier Lautstärkenanpassung** (Prozess-Crossfade) und separater Lautstärkeregelung.
   - **Adaptive SNR (Automatisches Störschall-Stufenverfahren)**: Dynamische Anpassung des Störschallpegels (+5% Lärm nach 3 richtigen Antworten / -5% bei Fehlern).
   - **Sprechtempo-Regelung**: Verlangsamtes oder beschleunigtes Sprechen (0.6x bis 1.4x).

7. **Hochwertige Sprachsynthese**:
   - Verwendet bevorzugt **Online-TTS** für sehr natürliche Sprachausgabe sowie native Betriebssystem-Stimmen (`Anna`, `Eddy`, `Flo`, `Sandy`, etc.) mit automatischem Cache Clean-Up (>7 Tage / >100 MB).

8. **Phonetische Auswertung (Kölner Phonetik)**:
   - Integrierter **Kölner Phonetik Algorithmus** zur Bewertung von Artikulationskategorien (Plosive, Frikative, Nasale, Vokaldifferenzierung) mit audiologischen Praxistipps.

---

## ⌨️ Tastatur-Hotkeys (Barrierefreie Steuerung)

Die Anwendung lässt sich vollständig ohne Maus über die Tastatur steuern:

| Taste | Funktion |
| :--- | :--- |
| <kbd>Leertaste</kbd> / <kbd>P</kbd> | Wort / Audio erneut abspielen |
| <kbd>1</kbd> | Option A auswählen (Minimalpaare / Sätze) |
| <kbd>2</kbd> | Option B auswählen (Minimalpaare / Sätze) |
| <kbd>Enter</kbd> | Eingabe prüfen (Einsilber & Zahlen) |
| <kbd>N</kbd> / <kbd>→</kbd> | Nächste Übung aufrufen |
| <kbd>M</kbd> | Mikrofon-Aufnahme starten (Nachsprechen) |
| <kbd>H</kbd> / <kbd>?</kbd> | **Online-Hilfe** öffnen / schließen |
| <kbd>Esc</kbd> | Hilfe-Fenster oder Eingabefelder verlassen |

---

## ❓ Online-Hilfe im Web-UI

Im Web-UI kann jederzeit über den Button **`❓ Hilfe & Hotkeys`** in der Kopfzeile oder per Taste <kbd>H</kbd> / <kbd>?</kbd> das Hilfe-Overlay geöffnet werden. Es bietet eine Übersicht aller Tastenkürzel sowie audiologische Trainingshinweise für den optimalen Einsatz des CI-Hörtrainers.

---

## 🧪 Tests ausführen

Die Unit-Tests zur Verifizierung aller Komponenten und des Kölner Phonetik Evaluators werden wie folgt ausgeführt:

```bash
python3 -m unittest discover tests
```
