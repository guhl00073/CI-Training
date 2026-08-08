# CI-Hörtrainer (Auditory Training System für CI-Träger)

Eine spezialisierte Python-Anwendung für das audio-phonetische Hörtraining von Cochlea-Implantat (CI) Trägern,

## Features & Übungsmodule

1. **Minimalpaar-Training**:
   - Unterscheidung phonetisch ähnlicher Wortpaare (z.B. *Pass / Bass*, *Tasse / Dasse*, *Haus / Maus*, *Kamm / Komm*).
   - Visuelle Auswertung von Konsonanten- und Vokaldifferenzierung.

2. **Einsilber-Training**:
   - Orientiert am Freiburger Einsilbertest (z.B. *Bus*, *Dach*, *Fisch*, *Brot*, *Strand*, *Herbst*).
   - Phonetisches Feedback mit automatischer Analyse von Anlaut, Vokal und Auslaut.

3. **Zahlen- & Betragsverständnis**:
   - Hörtraining für Einzelzahlen, zweistellige/dreistellige Zahlen, Uhrzeiten und Geldbeträge.

4. **CI-spezifische Audio-Steuerung**:
   - **Stereo-Balance / Kanalisolierung**: Getrennte Ansteuerung des linken oder rechten Ohrs (für bilateral oder bimodal versorgte CI-Träger).
   - **Sprechtempo-Regelung**: Verlangsamtes oder beschleunigtes Sprechen ohne Tonhöhenverzerrung.
   - **Lautstärkeregelung**.

5. **Hochwertige Sprachsynthese (Online & Native)**:
   - Verwendet bevorzugt **Online-TTS** für sehr natürliche Sprachausgabe sowie native macOS-Stimmen (`Anna`, `Eddy`, `Flo`, `Reed`, `Sandy`) für latenzfreie Offline-Nutzung.

6. **Fortschritts- & Fehleranalyse**:
   - Integrierte SQLite-Datenbank zur Aufzeichnung von Trefferquoten und Verlaufsstatistiken.

---

## Voraussetzung & Start

### Voraussetzungen

- **Python 3.9+** (Standardmäßig auf macOS installiert)

### Anwendung starten

```bash
python3 main.py
```
