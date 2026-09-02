# Release Notes – CI-Hörtrainer

## 📄 Release Update (2. September 2026) – Editor-Workflow & UI-Optimierungen

### 1. ✏️ Erweiterter Übungs-Editor & Workflow
* **Serien-Modus für schnelles Anlegen:** Eine neue Checkbox "⚡ Serien-Modus (Nächste anlegen)" im Editor ermöglicht es, nach dem Speichern einer neuen Übung das Formular direkt geöffnet zu lassen, um in Serie neue Wörter oder Sätze anzulegen.
* **Verbesserte Kategorie-Erstellung:** Das alte Autovervollständigungs-Feld (`datalist`) wurde durch ein robustes Dropdown (`select`) ersetzt. Neue Kategorien können nun direkt über das Kategoriemanagement-Fenster mit einem neuen Eingabefeld und einem "➕ Hinzufügen"-Button erstellt werden.

### 2. 🎨 UI/UX & Layout-Feinschliff
* **Nahtloses Glassmorphism-Design:** Wenn der Haupt-Trainingsbereich oder Audio-Visualizer aufgeklappt ist, verschmelzen die Kopfzeile und der Inhaltsbereich jetzt nahtlos ohne störende abgerundete Ecken in der Mitte.
* **Layout-Stabilität der Aktionsleiste:** Die "Pause"-Buttons verschwinden bei deaktiviertem Autostart nicht mehr komplett (was zuvor ein "Springen" der Buttons verursachte). Stattdessen werden sie visuell ausgegraut (disabled), um die Struktur der Aktionsleiste stabil zu halten.
* **Rundere Formen & Proportionen:** Allgemeine visuelle Aufwertung durch stärker abgerundete Aktions-Buttons (`border-radius: 20px`) und einheitliche Höhen für Text-Eingabefelder.

---

## 📄 Release Update (31. August 2026) – Logging, Stabilität & UI-Feinschliff

### 1. 📝 Implementierung Error Tracking (Logging-System)
* **Zentralisiertes Logging:** Komplett neues Logging-System (`src/utils/logger.py`) ersetzt alte Konsolenausgaben. 
* **Automatische Logdatei:** Fehler und Informationen werden nun parallel zur Konsole auch in einer persistierenden Logdatei im Nutzerverzeichnis (z. B. `%APPDATA%/CI-Hörtrainer/logs/ci_training.log`) gespeichert. Das hilft enorm bei der Fehlersuche.
* **Rotation & Speicherplatz-Schutz:** Der Dateilogger (`RotatingFileHandler`) limitiert Log-Dateien auf 5 MB und speichert maximal 3 Backups.
* **Live Log-Viewer im UI:** Über den neuen Button **"📜 Logs"** direkt oben im Header können Anwender nun die Fehler-Logs bequem in Echtzeit über ein Overlay-Fenster einsehen, ohne die eigentliche `.log`-Datei auf dem Computer suchen zu müssen.


### 2. 🛠️ Stabilitäts-Fixes (macOS / Windows / Permissions)
* **Windows Audio Fallback (`player.py`):** Behebt Crashes auf Windows, bei denen das fehlende Kommando `aplay` zu Abstürzen führte. Fällt nun sicher auf `ffplay` zurück. Verhindert das Aufpoppen schwarzer Konsolenfenster durch die Übergabe von `CREATE_NO_WINDOW`.
* **Sicheres Cache-Management (`tts_engine.py`):** Die Ordner-Erstellung und Aufräum-Mechanismen (`cleanup_cache`) wurden mit `try/except` gesichert, um Abstürze bei restriktiven Schreibrechten (z. B. in Sandboxes) zu verhindern.

### 3. 🎨 UI-Konsistenz & Frontend-Sicherheit
* **Vereinheitlichte Terminologie:** Sämtliche inkonsistenten Bezeichnungen für das Anhalten von Übungen ("Stop", "Stopp") wurden durchgängig durch **"⏸ Pause"** ersetzt und optisch angepasst (Bernsteingelb).
* **Sicheres JSON Parsing (`app.js`):** Fehlgeschlagene DOM-Klicks im Editor werfen keine JS-Exceptions mehr, da unvollständige `data`-Attribute nun von einem `try/catch` Block im Event-Listener sicher abgefangen werden.

---

## 📄 Release Update (28. August 2026) – Klinischer Therapeutenbericht & Pfad-Architektur

### 1. 📄 Klinischer Therapeutenbericht (Logopädie- & Audiologie-Export)
* **Umfassende Dokumentation für Logopäden & Audiologen:**
  * **Patienten- & Versorgungsprofil:** Name, Versorgungstyp (Bilateral, Monoral, Bimodal, SSD), CI-Implantat-Modell, Erstanpassungsdatum (EA), Wort-Lautstärke und Sprechtempo.
  * **KPI-Zusammenfassung:** Trefferquote (%), Gesamtübungsanzahl, gewichteter Durchschnittsscore, aktive Trainingstage und Datumsbereich.
  * **Logopädischer Therapie-Fokus:** Automatische Auswertung zur Identifikation von Lautkontrast-Schwachstellen (z. B. Plosive, Frikative, Nasale), die im Therapiealltag gezielt geübt werden sollten.
  * **Sprachaudiometrie-Historie:** Übersicht der Ergebnisse des Freiburger Einsilbertests (DIN 45621) und adaptive OLSA SRT Testergebnisse in dB SNR.
  * **🖨️ Drucken & PDF-Export:** Nativer Druck-Button mit speziell optimierten `@media print`-CSS-Regeln für saubere, weiße klinische Ausdrucke oder PDF-Erstellung.

### 2. 🛠️ Pfad-Architektur & Standalone App Bundles
* **Vollständige Integration von statischen Ressourcen:** `get_resource_path()` löst gebündelte Ressourcen (Audio-Dateien, JSON-Übungen, Weboberfläche) zur Laufzeit über `sys._MEIPASS` auf. Dies verhindert zuverlässig das unbeabsichtigte Erstellen eines externen `/data`-Ordners auf der Festplatte.
* **Standardsystem-Ordner für Benutzerdaten:** Die SQLite-Datenbank (`ci-training.db`) und der Audio-Cache werden automatisch in den vom Betriebssystem vorgegebenen Anwendungsdaten-Verzeichnissen gespeichert:
  * **macOS:** `~/Library/Application Support/CI-Hörtrainer/`
  * **Windows:** `%APPDATA%\CI-Hörtrainer\`

### 3. 📦 Bündelung in Executable Apps & Release-Automatisierung
* **Eigenständige Ausführbare Anwendungspakete (PyInstaller):**
  * **macOS (`CI-Hörtrainer-macOS.zip`):** Nativer `.app`-Bundle mit integriertem Python-Laufzeitumfeld und Launcher-Skript (`CI-Hörtrainer.app`).
  * **Windows (`CI-Hörtrainer-Windows.zip`):** Vollständiges Executable-Paket (`CI-Hörtrainer.exe`) inklusive aller Abhängigkeiten ohne Notwendigkeit einer manuellen Python-Installation.
* **Manuell gesteuerte GitHub Releases Workflow (`.github/workflows/build_executables.yml`):**
  * Die automatische Paketerstellung wird gezielt nur bei manueller Ausführung (Workflow Dispatch) oder beim Setzen eines offiziellen Git-Releasetags (`v*.*.*`) getriggert.
  * Normale Code-Commits auf den `main`-Branch lösen keine unbeabsichtigte Erstellung neuer App-Releases aus.
  * Fokussierung auf die ausgiebig getesteten Zielplattformen macOS und Windows (Deaktivierung der ungetesteten Linux-Build-Matrix).

---

## 🚀 Release Update (26. August 2026) – Azure Neural Stimmen, DIN 45621 Wortschatz, Auto-Mic & Umfassende Testsuite

### 1. 🌐 Microsoft Azure Neural Studio-Stimmen (`edge-tts`)
* **10 authentische deutschsprachige Studio-Sprecher (48 kHz):**
  * 🇩🇪 **Deutschland:**
    * 👨 **Conrad:** Männlich Natürlich & Kräftig *(Standard-Empfehlung für Männerstimmen)*
    * 👨 **Florian:** Männlich Klar & Modern
    * 👨 **Killian:** Männlich Dynamisch
    * 👩 **Katja:** Weiblich Klar & Prägnant
    * 👩 **Amala:** Weiblich Sanft & Natürlich
    * 👩 **Seraphina:** Weiblich Fein & Ausgewogen
  * 🇦🇹 **Österreich (Regionale Klangfarben fürs Hörtraining):**
    * 👨 **Jonas:** Männlich Natürlich
    * 👩 **Ingrid:** Weiblich Natürlich
  * 🇨🇭 **Schweiz (Regionale Klangfarben fürs Hörtraining):**
    * 👨 **Jan:** Männlich Natürlich
    * 👩 **Leni:** Weiblich Natürlich
* **100 % Freeware & Datenschutz:** Direkte Synthese ohne Registrierung und ohne API-Key.
* **Fokus auf echte deutsche Muttersprachler:** Vollständige Entfernung unpassender englisch-basierter Phonemtransfers (Kokoro) sowie veralteter 80er-Jahre MacinTalk-Stimmen.

---

### 2. 💻 Dynamische Erkennung installierter System-Stimmen (macOS & Windows)
* **macOS (Nativ & Latenzfrei):**
  * Automatischer Scan aller heruntergeladenen deutschen Qualitätsstimmen (*Anna Premium, Markus Verbessert, Petra Premium, Viktor Verbessert, Yannick*).
  * Filterung von 26 veralteten 80s/90s Novelty-Roboterstimmen.
* **Windows (OneCore & SAPI5):**
  * Automatische Erkennung moderner Windows 10/11 Sprachpakete (WinRT OneCore: *Katja, Conrad*) und Desktop-SAPI5 (*Hedda, Stefan*).
* **🔊 Sofortiges Probehören:** Neuer Button `🔊 Stimme testen` direkt neben der Stimmenauswahl.

---

### 3. 🎙️ Auto-Mic Fehlerbehebung & Optimierung bei Mehrsilbern & Komposita
* **Intelligente Silben- und Vokalcluster-Dauerberechnung (`estimateSpeechDurationMs`):**
  * Präzise Berechnung der Vorlesedauer für 2-, 3-, 4- und mehrsilbige Wörter sowie lange Komposita (z. B. *Straßenbahnhaltestelle*, *Kindergarten*).
  * Verhindert verfrühtes Einschalten des Mikrofons während der laufenden Audioausgabe.
* **Vollständige Modul-Verknüpfung:** Nahtlose Integration des Mehrsilber-Tabs (`ms`) in den Spracherkennungs-Lifecycle: Eingabefeld (`#msInput`), Button (`#msMicBtn`), Klick-Handler, Reset-Routine und automatische Auswertung mit `checkMSAnswer()`.

---

### 4. 📚 DIN 45621 Wortschatz-Erweiterung & Mehrsilber-Diagnostik
* **400 Freiburger Einsilber (DIN 45621):** Alle 20 offiziellen Prüflisten à 20 Wörter mit ausgewogener phonetischer Lautverteilung.
* **100 Freiburger Zahlen (DIN 45621 Zahlentest):** Alle 10 standardisierten Zahlenlisten à 10 zweisilbige Testzahlen.
* **70 Mehrsilber & Komposita:** Didaktische Wortschatzerweiterung für 2-, 3- und 4-silbige Wörter mit automatischer Silbenzählung und visueller Silbentrennung (z. B. *Kin·der·gar·ten*).
* **Automatisierter Seed-Prozess:** Konsistente Datenbank-Initialisierung aller 1279 Vokabeln über `scripts/generate_vocabularies.py` und `scripts/seed_database.py`.

---

### 5. 🎙️ Google Cloud Sprachsynthese & Akustik-Modeling
* **Verlustfreie 22.05 kHz WAV-Synthese:** Hohe Natürlichkeit und Konsonantenschärfe ohne MP3-Kompressionsartefakte.
* **Akustisches Formant- und Tempomodeling:** Stufenlose Anpassung des Sprechtempos (0.6x bis 1.4x) und automatischer nativer Fallback bei Offline-Betrieb.

---

### 6. 🧪 Umfassende Testsuite für alle 12 Module & REST-API
* **67 automatisierte Unit- und Integrationstests:**
  * `tests/test_all_11_modules.py`: Vollständige logische und audiologische Tests aller 12 Module.
  * `tests/test_api_endpoints.py`: Integrationstests aller 30+ REST-API-Endpunkte.
  * `tests/test_tts_engine.py` & `tests/test_freiburger_and_multisyllables.py`: Tests für Sprachmodelle, Cache-Bereinigung und DIN-Prüflisten.

---

## 🚀 Release Update (25. August 2026) – Multi-User Profilmanagement, Seitengetrennte CI-Versorgung & Audio-Optimierungen

### 1. 👤 Multi-User & CI-spezifisches Profilmanagement

* **Vollständige Profilverwaltung (`user_profiles` SQLite-Tabelle):**
  * Schneller Profilwechsel direkt über den oberen Header-Button `[ 👤 <Profilname> | <Versorgungstyp> ▾ ]` oder Hotkey <kbd>Alt+P</kbd> / <kbd>⌥P</kbd> / <kbd>U</kbd>.
  * Neuanlage, Bearbeitung und sicheres Löschen von Profilen (Schutz des jeweils letzten Standardprofils).
* **Seitengetrennte Versorgungstypen:**
  * 🦻 **Monoral Rechts / Links:** Gezielte Balance-Ausrichtung auf die implantierte Seite.
  * 🦻🦻 **Bilateral:** Ausgewogene oder seitengetrennte CI-Beschallung.
  * 🦻 **Bimodal Rechts / Links:** Unterscheidung nach CI-Seite und Hörgeräte-Gegenohr (z. B. *CI Rechts + HG Links*).
  * 🦻 **SSD Rechts / Links (Single Sided Deafness):** Einseitig taub / CI-versorgt mit normalhörendem Gegenohr inklusive automatischer Balance- und Vertäubungs-Unterstützung.
* **Prozessor- & Modell-Katalog (Dropdown):**
  * Strukturierte Modellauswahl für **Cochlear** (*Nucleus 8/7/6, Kanso 2/1, Osia 2*), **MED-EL** (*Sonnet 3/2/1, Rondo 3/2, Samba 2*), **Advanced Bionics** (*Naída CI Marvel, Sky CI Marvel, Q90, Chorus, Neptune*), **Oticon Medical** (*Neuro 2/1, Ponto 5*) und individuelle Systeme.
* **Echtzeit-Synchronisation aller Audio-Einstellungen pro Profil:**
  * Sämtliche Einstellungen aus dem Bereich *„⚙️ Audio-Einstellungen & Rauschen“* werden **ohne separaten Speicher-Dialog automatisch im aktiven Profil hinterlegt**:
    * Wort-Lautstärke (`master_gain`), Rausch-Lautstärke (`noise_volume`), Sprechtempo (`speech_rate`), Stimme (`voice`), Vertäubung (`mask_noise`), Stereo-Balance (`audio_balance`), Audio-Frequenzfilter (`freq_filter`), Autostart-Pausenzeiten (`autostart_success_delay`, `autostart_error_delay`) und Freisprechen (`auto_mic`).

---

### 2. 🌊 Störschall-Training: Audiometrische SNR-Konsolidierung & stabiles Audio-Streaming

* **Audiometrisch exakte Signal-to-Noise Ratio (SNR in dB):**
  * Doppelte Lautstärkeregler entfernt und auf klinisch definierte SNR-Stufen vereinheitlicht:
    * `+10 dB SNR` (*Sehr leicht / Einstieg*)
    * `+5 dB SNR` (*Leicht*)
    * `0 dB SNR` (*Klinischer Standard*)
    * `-5 dB SNR` (*Fortgeschritten / Anspruchsvoll*)
* **Kein Audio-Abbruch beim Nachjustieren:**
  * Der Störschall (Restaurant, Cafeteria, Straßenlärm) läuft nun kontinuierlich und unterbrechungsfrei weiter, wenn SNR-Stufen oder Rauschpegel während der Übung angepasst werden.

---

### 3. 🧠 Auditives Gedächtnis: Gesicherte Sequenz-Wiedergabe

* **Karten-Sperre während des Vorlesens:**
  * Um ein unabsichtliches Vorweggreifen zu verhindern, sind die Wort-Karten und Interaktions-Buttons während des Abspielens der auditiven Sequenz gesperrt und mit einem Hinweisbanner (*„🎧 Sequenz wird vorgelesen...“*) versehen.
  * Erst nach Abschluss der vollständigen Wortfolge werden die Karten zur auditiven Erinnerung und Auswahl freigegeben.

---

### 4. 🎙️ Mikrofon- & Spracherkennungs-Optimierungen

* **Freiburger Testlisten:**
  * Behebung des Problems, dass die Spracherkennung nach dem ersten Wort bei Folgewörtern blockierte.
* **Echtzeit-Spektrum für Spracheingabe:**
  * Der Audio-Spektrumanalysator visualisiert nun sowohl die TTS-Audioausgabe als auch die eigene Spracheingabe über das Mikrofon.
* **Globaler Freisprech-Schalter (`auto_mic`):**
  * Automatische Mikrofon-Aktivierung nach Übungsstart lässt sich global in den Audio-Einstellungen ein- und ausschalten.

---

### 5. 🎨 Umfassendes UI-Redesign & Typografie-Optimierung

* **Harmonisierte Textgrößen & Ergonomie:**
  * Schriftgrößen im gesamten Interface wurden gezielt verringert und harmonisiert, um die Übersichtlichkeit auf Desktop- und Laptop-Monitoren deutlich zu verbessern.
  * Kompaktere Abstände und konsistentes Glassmorphism-Design mit modernen Kontrasten.
* **Modernisierte Header-Statusleiste:**
  * Oben rechts sauber integriert: Interaktiver Profil-Button `[ 👤 <Name> | <Versorgung> ▾ ]`, Hilfe & Hotkeys-Button (`❓`), Level-Badge und Beenden-Button (`✕`).
* **Visuelle Feedback-Banner & Countdown:**
  * Responsive Erfolgs- und Fehler-Banner mit Countdown-Balken, IPA-Lautschrift und Hover-/Klick-Pausenfunktion.

---

### 6. ✏️ Erweiterter Übungs-Editor & Globaler Kategoriemanager

* **Globaler Kategoriemanager (`categoryManagerModal`):**
  * Eigene Kategorien modulübergreifend umbenennen oder leere Kategorien bereinigen.
* **Live-Filter mit Elementzähler im Editor:**
  * Schneller Kategorie-Filter in der Editor-Toolbar mit automatischer Zählanzeige (z. B. `P vs. B (24)`).
* **Autovervollständigung (`datalist`):**
  * Vorhandene Kategorien werden bei der Eingabe neuer Übungen automatisch als Vorschläge angeboten.
* **Kompakte Toolbar:**
  * Toolbar-Höhe und Abstände vereinheitlicht für schnelles Arbeiten im Tabellen-Editor.

---

### 7. ⌨️ Hotkey-Harmonisierung & Fehlerbereinigungen

* **Hotkey-Konflikt gelöst:**
  * <kbd>Leertaste</kbd> / <kbd>P</kbd> bleibt exklusiv für das erneute Abspielen des aktuellen Audio-Signals reserviert (`replayCurrentAudio`).
  * Profil-Manager wird ergonomisch über <kbd>Alt+P</kbd> (macOS: <kbd>⌥P</kbd>) oder die Taste <kbd>U</kbd> (*User*) geöffnet.
* **Einsilber-Moduswahl:**
  * Modus-Umschaltung setzt den Start-Button wieder korrekt auf den Ausgangszustand zurück.

---

## 🌟 Frühere Features & Highlights

Vielen Dank an Ingo für das ausführliche Testen und die zahlreichen Anregungen und Fehlerberichte.

### 1. ⌨️ Vollständige Plattformübergreifende Hotkey-Steuerung (macOS, Windows, Linux)

* **Plattformunabhängige Hardware-Tastenerkennung (`e.code`):**
  * Behebt Probleme auf macOS, bei denen die `Option/Alt`-Taste Sonderzeichen erzeugt hat.
  * Unterstützt native Tastenkürzel für macOS (<kbd>⌥</kbd> / <kbd>⌘</kbd>) sowie Windows & Linux (<kbd>Alt</kbd> / <kbd>Strg</kbd>).
  * Volle Unterstützung für **Ziffernblock / Numpad-Tasten** (`Numpad 1..6`, `Numpad Enter`).
* **Mouseover-Tooltips:** Jeder Button zeigt bei Mausberührung das jeweilige Tastenkürzel in einem Tooltip-Badge an.
* **Online-Hilfe & Hotkey-Übersicht:** Neues, ausführliches Hilfe-Modal erreichbar über <kbd>F1</kbd>, <kbd>H</kbd> oder <kbd>?</kbd>.

### 2. ⏱️ Intelligente Adaptive Autostart-Verzögerung mit Pause & Countdown

* **Adaptive Verweildauer:**
  * Bei **richtiger Antwort:** Kurze Pause (*Standard: 1,8 s*).
  * Bei **falscher Antwort:** Längere Pause (*Standard: 5,0 s*), um Phonetik, IPA-Lautschrift und Erklärung in Ruhe zu erfassen.
* **Visueller Countdown-Balken:** Ein dynamischer Fortschrittsbalken im Feedback-Banner visualisiert die verbleibende Zeit.
* **Pausen-Optionen:**
  * **Hover-Pause:** Maus über das Banner friert den Timer sofort ein.
  * **Klick-Pause:** Ein Klick auf das Banner oder den `⏸ Pause`-Knopf hält den Countdown an.
  * **Audio-Wiederholung (<kbd>Leertaste</kbd> / <kbd>P</kbd>):** Stoppt den Auto-Wechsel, sodass Sie das Wort ohne Zeitdruck erneut anhören und vergleichen können.
* **Konfigurierbar:** Beide Zeiten (Erfolg & Fehler) lassen sich im Bereich *„⚙️ Audio- & Trainings-Einstellungen“* stufenlos anpassen und werden dauerhaft im Browser gespeichert.

### 3. 🎯 1-Klick-Workflow für Übungen

* Der Button **„Nächste Übung ➔“** lädt das neue Element und spielt die Audio-Ausgabe **sofort automatisch** ab – kein zweiter Klick auf *„Abspielen“* mehr nötig.
* Ein separater Button **„🔄 Wiederholen“** steht für erneutes Anhören bereit.

### 4. 🔢 Zahlen- & Ziffern-Erkennung (Wort vs. Ziffer)

* Die phonetische Auswertung akzeptiert Zahlwörter (*„zehn“*, *„einundzwanzig“*) und arabische Ziffern (*„10“*, *„21“*) vollständig gleichwertig.
* Funktioniert sowohl bei Einzeleingaben als auch in Ganzsatz-Diktaten.

### 5. ✏️ Erweiterter Übungs-Editor mit Kategorie-Filter

* **Dynamische Kategorie-Auswahl:** Neu angelegte oder bearbeitete Kategorien erscheinen sofort im Auswahl-Dropdown der Übungsmodule (z. B. bei den Minimalpaaren).
* **Dropdown-Filter im Editor:** Neben der Textsuche steht in der Editor-Toolbar nun eine Kategorie-Filterliste mit automatischer Anzahl-Anzeige zur Verfügung (z. B. `Gerald (1)`, `P vs. B (24)`).
* **Autovervollständigung (`datalist`):** Im Editor-Eingabefeld werden bestehende Kategorien automatisch als Vorschläge angeboten.
* **Kompaktes Toolbar-Design:** Die Bauhöhe und Abstände aller Werkzeugeleiste-Elemente inklusive des *„➕ Neu“*-Buttons wurden vereinheitlicht.

### 6. 🛑 Beenden-Knopf & Server-Shutdown

* Roter **✕ Beenden-Knopf** oben rechts in der Kopfleiste (Hotkey: <kbd>Q</kbd>) zum sauberen Herunterfahren des lokalen Python-Servers und Schließen der App.
* Doppelter Button *„Schwachstellen“* in der Kopfleiste entfernt und sauber im Hauptmenü belassen.

### 7. 🔒 Thread-Safety, Sicherheit & Cross-Platform Audio-Engine

* **Vollständige SQLite Thread-Safety:**
  * Alle Datenbankoperationen in `ProgressDatabase` sind nun durch atomare Thread-Locks (`threading.RLock`) geschützt. Verhindert Deadlocks und Concurrency-Fehler bei parallelen REST-Anfragen.
* **DIN 45621 Freiburger-Listen-Integrität:**
  * Korrigierte Sortierung (`ORDER BY rowid ASC`) stellt sicher, dass die 20er-Wortlisten der Freiburger Tests in exakter DIN-Norm-Reihenfolge abgespielt werden.
* **Universelle Audio-Aufnahme (macOS, Windows, Linux):**
  * Plattformspezifische Audio-Backends (`avfoundation` auf macOS, `dshow` auf Windows, `alsa` auf Linux).
  * Dynamisches FFmpeg-Discovery (`shutil.which` + plattformübergreifende Fallbacks) ersetzt alle hardcodierten macOS-Pfade.
  * Sichere temporäre Dateierstellung via `tempfile.mkstemp`.
* **Path-Traversal-Schutz:**
  * Robuste Absicherung des Bild-Upload-Endpunkts (`/api/upload_image`) gegen unzulässige Pfadmanipulationen.

### 8. 🗣️ Erweiterter Zahlenkomposita-Parser & IPA-Synchronisation

* **Zusammengesetzte Zahlwörter & Währungen:**
  * Neuer deutscher Zahlenkomposita-Parser (`parse_german_number_word`) verarbeitet komplexe Wortzahlen wie *„einhundertfünfundzwanzig“* (125), *„zweihundertzehn“* (210) oder *„dreitausendzweihundert“* (3200) sowie Schweizer Schreibweisen (*„dreissig“*).
  * Vollständige Äquivalenzerkennung für Währungsbeträge (*„15 €“*, *„15 Euro“*, *„12,50 €“*, *„3 Euro 85 Cent“*) und Uhrzeitformate (*„14:30 Uhr“*).
* **Asynchrone IPA-Synchronisation:**
  * Neuer Backend-Endpunkt `GET /api/ipa?word=...` liefert detaillierte IPA-Lautschrift, Artikulationsort und logopädische Hinweise.
  * Das Frontend nutzt einen In-Memory-Cache für verzögerungsfreies Rendering und dynamische Tooltip-Erweiterungen.

### 9. 🧹 Bereinigung von Legacy-Code

* Das veraltete, nicht mehr genutzte Tkinter-Modul `src/ui/` (`desktop_app.py`) wurde entfernt. Die Anwendung ist nun vollständig und sauber auf die moderne Web-Applikation fokussiert.

### 10. 🎯 Klinische Audiologie: Adaptiver OLSA-Satztest (Brand & Kollmeier 2002)

* **Adaptiver Sprachverstehenstest:** Bestimmung der 50% Sprachverstehensschwelle im Störlärm (SRT in dB SNR) mittels 5-Wort-Matrixsätzen (*Name + Verb + Zahl + Adjektiv + Nomen* aus 100.000 möglichen Kombinationen).
* **Format-unabhängiges Audio-Mixing:** Automatische Konvertierung von MP3/AIFF-Sprachsynthesen in 16-Bit PCM-WAV vor der exakten SNR-Rauschmischung.
* **Konfigurierbarer Einstiegs-Schwierigkeitsgrad:** Startpegel wählbar zwischen `+5.0 dB SNR (Leicht / CI-Einstieg)`, `0.0 dB SNR (Klinischer Standard / Gleich laut)`, `+10.0 dB SNR (Sehr leicht)` und `-5.0 dB SNR (Fortgeschritten)`.
* **Live-Treppenplot & Auswertung:** Interaktives 5-Spalten-Interface, HTML5-Canvas-Treppenverfahren-Plot, automatische Wendepunkt-Erkennung (Reversals) und klinische Zertifikatskarte mit Standardabweichung und SRT-Bewertung.

### 11. 📈 Freiburger DIN-45621 Mehrpegel-Sprachaudiometrie & 65 dB Kalibrierung

* **Mehrpegel-Sprachverständlichkeit:** Messung bei 50 dB (leise), 65 dB (Zimmerlautstärke) und 80 dB (laut) mit Vergleich zur DIN-Normalhörenden-Referenzkurve, $V_{\max}$ (maximales Sprachverstehen) und Diskriminationsverlust.
* **🔊 65 dB SPL Lautstärke-Kalibrierungs-Assistent:**
  * Schritt-für-Schritt-Führung für Lautsprecher (1 m Freifeld mit Smartphone-Pegelmesser), Kopfhörer (Muschel-Kopplung) und direktes CI-Streaming (60–70% Systempegel).
  * Web-Audio-Generator für sprachgeformtes CCITT-Rauschen und 1 kHz Sinuston (-20 dBFS) mit Statusspeicherung in `localStorage`.

### 12. 🎛️ CI-Vocoder Simulation (Tonotope Greenwood-Filterbank)

* **Reine Sinuston-Resynthese (Sine-Wave Vocoder):** Zerlegung des Sprachsignals in frequenzselektive Bandpasskanäle entlang der humanen Cochlea (Greenwood 1990) und Einhüllenden-Modulation reiner Sinustöne.
* **Hersteller-Profile & Kanalstufen:**
  * 🦻 **Cochlear Nucleus:** 22 Kanäle
  * 🦻 **Advanced Bionics HiRes:** 16 Kanäle
  * 🦻 **MED-EL Synchrony:** 12 Kanäle
  * 🎯 **Hörtraining Fokus:** 8 Kanäle
  * 🔬 **Extrem verarmt:** 4 Kanäle
* **Direkte Echtzeit-Integration:** Wirkt sofort auf alle Übungen (Minimalpaare, Einsilber, Sätze) zur didaktischen Hörerfahrung und gezielten Schärfung des Sprachzentrums.

---

## 🐛 Bugfixes & Stabilitäts-Optimierungen

* **Format-Mismatch beim OLSA-Mixing behoben:** MP3-TTS-Ausgaben werden automatisch vor dem Einlesen in temporäre 16-Bit PCM WAV-Signale gewandelt (`RIFF`-Header Fix).
* **Automatischer Port-Cleanup & Prozess-Lifecycle:** `start_ci_trainer.sh` und `server.py` lösen Socket-Blockaden (Port 8080) automatisch auf, wecken pausierte Shell-Jobs (`^Z`) via `SIGCONT` auf und beenden sie sauber.
* **Layout-Bereinigung der Audio-Einstellungen:** Behebung eines ungeschlossenen HTML-Tags in der Steuerleiste; alle Schalter (Adaptive SNR, Sprecherstimme, Vocoder, 65 dB Kalibrierung) sind wieder sauber zweispaltig angeordnet.
* **Eingabe-Validierung:** Bei Klick auf *„Prüfen“* ohne Texteingabe wird die Übung nicht mehr fälschlicherweise als falsch gewertet oder gesperrt.
* **Statistik- & Thread-Integrität:** SQLite-Zugriffe durch atomare `RLock`-Sperren abgesichert.

---

### 📦 Geänderte / Betroffene Dateien

* `src/audio/olsa_adaptive.py` – Adaptiver OLSA-Algorithmus (Brand & Kollmeier 2002), FFT/Filterbank & WAV-Mixer
* `src/audio/ci_vocoder.py` – Greenwood-Filterbank, Hüllkurven-Extraktion & reine Sinus-Resynthese
* `src/database/progress_db.py` – Thread-Synchronisation (`RLock`), OLSA- (`olsa_test_runs`) & Audiogramm-Tabellen (`freiburger_audiograms`)
* `src/audio/recorder.py` – Cross-Platform Audio-Aufnahme (`avfoundation`, `dshow`, `alsa`) & sichere Temp-Dateien
* `src/audio/tts_engine.py` – Dynamisches FFmpeg-Discovery, Pitch-Modulation & MP3/WAV-Erzeugung
* `src/audio/player.py` – System-Audio-Wiedergabe, kontinuierliche Vertäubung & Störschall-Synchronisation
* `src/evaluator/phonetic_matcher.py` – Rekursionsfreier deutscher Zahlenkomposita-, Währungs- & Zeitparser
* `src/web/server.py` – Path-Traversal-Schutz, Port-Cleanup, IPA-, OLSA-, Audiogramm- & Vocoder-Endpunkte
* `src/web/static/app.js` – OLSA Matrix & Live-Staircase-Plot, Audiogramm DIN-45621, 65 dB Kalibrierungs-Assistent, Vocoder-Steuerung
* `src/web/static/index.html` – Tabs für OLSA & Audiogramm, 65 dB Kalibrierungs-Modal, Vocoder-Panel
* `src/web/static/styles.css` – 5-Spalten OLSA-Grid, Audiogramm- & Kalibrierungs-Styling
* `start_ci_trainer.sh` – Automatischer Port-8080-Cleanup und robuster Starter
* `tests/test_components.py` – Umfassende Testsuite (23/23 Tests bestanden)
