#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================="
echo "Starte CI-Hoertrainer"
echo "======================================================="

# Pfad fuer Homebrew auf macOS ergaenzen (Apple Silicon / Intel), falls nicht im PATH
if [ -x "/opt/homebrew/bin/brew" ]; then
    export PATH="/opt/homebrew/bin:$PATH"
elif [ -x "/usr/local/bin/brew" ]; then
    export PATH="/usr/local/bin:$PATH"
fi

# 1. Pruefen, ob Python 3 / Python installiert ist (sonst via Homebrew installieren)
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[WARNUNG] Python ist auf diesem System noch nicht installiert."
    if command -v brew &>/dev/null; then
        echo "[INFO] Homebrew wurde gefunden. Installiere Python via Homebrew..."
        brew install python
        if command -v python3 &>/dev/null; then
            PYTHON_BIN="python3"
        elif command -v python &>/dev/null; then
            PYTHON_BIN="python"
        else
            echo "[FEHLER] Fehler: Python konnte via Homebrew nicht installiert werden."
            exit 1
        fi
    else
        echo "[INFO] Homebrew ist ebenfalls nicht installiert. Versuche Homebrew & Python zu installieren..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -x "/opt/homebrew/bin/brew" ]; then
            export PATH="/opt/homebrew/bin:$PATH"
        elif [ -x "/usr/local/bin/brew" ]; then
            export PATH="/usr/local/bin:$PATH"
        fi
        if command -v brew &>/dev/null; then
            brew install python
            PYTHON_BIN="python3"
        else
            echo "[FEHLER] Fehler: Neither Python 3 nor Homebrew could be installed automatically."
            echo "Bitte installieren Sie Python 3 (https://www.python.org/) oder Homebrew (https://brew.sh/)."
            exit 1
        fi
    fi
fi

echo "[OK] Python gefunden: $($PYTHON_BIN --version)"

# 2. Pruefen, ob eine virtuelle Umgebung (.venv) existiert (und ggf. erstellen)
VENV_DIR="$DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[WARNUNG] Keine virtuelle Umgebung (.venv) gefunden. Erstelle eine neue .venv..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo "[OK] Virtuelle Umgebung (.venv) erfolgreich erstellt."
    else
        echo "[FEHLER] Fehler beim Erstellen der virtuellen Umgebung (.venv)."
        exit 1
    fi
else
    echo "[OK] Virtuelle Umgebung (.venv) vorhanden."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[FEHLER] Fehler: Python Executable in $VENV_DIR nicht gefunden."
    exit 1
fi

# 3. Pruefen und Installieren der erforderlichen Pakete via requirements.txt
REQUIREMENTS_FILE="$DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Ueberpruefe und installiere Abhaengigkeiten aus requirements.txt..."
    "$VENV_PIP" install -r "$REQUIREMENTS_FILE" --quiet || echo "[HINWEIS] Hinweis: Abhaengigkeiten konnten nicht direkt installiert werden (z. B. offline)."
    echo "[OK] Abhaengigkeitspruefung abgeschlossen."
else
    echo "[WARNUNG] Warnung: requirements.txt wurde nicht gefunden!"
fi

# 4. Alte/pausierte Prozesse auf Port 8080 bereinigen
if command -v lsof &>/dev/null; then
    OLD_PIDS=$(lsof -ti :8080 2>/dev/null)
    if [ -n "$OLD_PIDS" ]; then
        echo "[INFO] Gebe belegten Port 8080 frei..."
        for p in $OLD_PIDS; do
            kill -CONT "$p" 2>/dev/null || true
            kill -15 "$p" 2>/dev/null || true
        done
        sleep 0.3
        for p in $OLD_PIDS; do
            kill -9 "$p" 2>/dev/null || true
        done
    fi
fi

# 5. Hauptanwendung starten
echo "======================================================="
echo "Starte Hauptanwendung..."
echo "======================================================="
cleanup_on_exit() {
    pkill -P $$ 2>/dev/null || true
}
trap cleanup_on_exit EXIT INT TERM
"$VENV_PYTHON" "$DIR/main.py"

