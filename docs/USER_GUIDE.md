# CI-Hörtrainer – Benutzerhandbuch

Willkommen beim **CI-Hörtrainer**, der spezialisierten Anwendung für das auditive Hörtraining von Cochlea-Implantat (CI) Trägern und Hörgeräteträgern.

---

## 🎯 Übungsmodule

### 1. Minimalpaare
- **Ziel:** Unterscheidung phonetisch ähnlicher Wortpaare (z. B. *P vs. B*, *T vs. D*, *F vs. W*, *W vs. B*, *S vs. Z*, *N vs. NG*, *CH vs. SCH*, *Vokallänge*).
- **Ablauf:** Höre das vorgelesene Wort und wähle aus den angezeigten Karten die richtige Antwort.
- **Fokus-Auswahl:** Über das Dropdown-Menü kann gezielt nach bestimmten Lautpaaren oder Vokallängen gefiltert werden.

### 2. Einsilber (Freiburger Test)
- **Ziel:** Präzises Verstehen von einsilbigen Wörtern in ruhiger Umgebung.
- **Phonetische Analyse:** Das System analysiert Anlaut, Vokal und Auslaut und gibt detailliertes Feedback.

### 3. Zahlen, Uhrzeiten & Geldbeträge
- **Ziel:** Verstehen von Zahlwörtern, zweistelligen/dreistelligen Zahlen, Uhrzeiten (z. B. *14:30 Uhr*) und Geldbeträgen (*12,50 €*).

### 4. Sätze & Kontext
- **Ziel:** Satzverständnis und Wortidentifikation im Satzkontext.

### 5. Störschall-Training (Noise)
- **Ziel:** Hören unter erschwerten Bedingungen im Alltags-Lärm.
- **Hintergrundgeräusche:** Auswahl zwischen Rauschen, Restaurant, Café, Straßenverkehr, Bahnhof und Unterhaltung (Chatter).

### 6. Auditives Gedächtnis (Merkspanne & Sequenzen)
- **Ziel:** Schulung der auditiven Merkspanne und Reihung.
- **Ablauf:** Eine Sequenz aus 2 bis 6 Wörtern wird nacheinander vorgelesen. Anschließend müssen die Wörter in der exakten Reihenfolge ausgewählt werden.

---

## 🎧 Audio-Steuerung für CI-Träger

- **Stereo-Balance (Kanalisolierung):** 
  - `-1.0` (Nur Links) / `+1.0` (Nur Rechts) / `0.0` (Stereo Mitte).
  - Ermöglicht das gezielte Training des CI-Ohrs bei unilateraler oder bimodalem Versorgung (CI + Hörgerät).
- **Vertäubung (Masking):** 
  - Sendet kontinuierliches Gegenrauschen auf das Nicht-CI-Ohr, um Überhören zu vermeiden.
- **Sprechtempo-Regelung:**
  - Verlangsamung (`0.7x` bis `0.9x`) oder Beschleunigung (`1.1x` bis `1.5x`) ohne Tonhöhenverzerrung.

---

## 🚀 Anwendung starten

```bash
# Web-Interface & Desktop-App starten
python3 main.py
```
Öffne im Browser: `http://localhost:8080`
