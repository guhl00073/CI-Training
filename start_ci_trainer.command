#!/bin/bash
# CI-Hoertrainer macOS Double-Clickable Executable Launcher

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "   Starte CI-Hoertrainer..."
echo "=================================================="

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
            read -p "Druecke Enter zum Beenden..."
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
            echo "[FEHLER] Fehler: Python 3 und Homebrew konnten nicht automatisch installiert werden."
            echo "Bitte installieren Sie Python 3 (https://www.python.org/) oder Homebrew (https://brew.sh/)."
            read -p "Druecke Enter zum Beenden..."
            exit 1
        fi
    fi
fi

echo "[OK] Python gefunden: $($PYTHON_BIN --version)"

# 2. Pruefen, ob eine virtuelle Umgebung (.venv) existiert (und ggf. erstellen)
VENV_DIR="$DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[WARNUNG] Virtuelle Umgebung (.venv) existiert nicht. Erstelle .venv..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[FEHLER] Fehler beim Erstellen der virtuellen Umgebung (.venv)."
        read -p "Druecke Enter zum Beenden..."
        exit 1
    fi
    echo "[OK] Virtuelle Umgebung (.venv) erfolgreich erstellt."
else
    echo "[OK] Virtuelle Umgebung (.venv) vorhanden."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[FEHLER] Fehler: Python Executable in $VENV_DIR nicht gefunden."
    read -p "Druecke Enter zum Beenden..."
    exit 1
fi

# 3. Pruefen und Installieren der erforderlichen Pakete via requirements.txt
REQUIREMENTS_FILE="$DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Ueberpruefe und installiere Abhaengigkeiten aus requirements.txt..."
    "$VENV_PIP" install -r "$REQUIREMENTS_FILE" --quiet || echo "[HINWEIS] Hinweis: Einige Pakete konnten nicht installiert werden (z. B. offline)."
    echo "[OK] Abhaengigkeitspruefung abgeschlossen."
else
    echo "[WARNUNG] Warnung: requirements.txt wurde nicht gefunden!"
fi

echo "=================================================="
echo "Starte Hauptanwendung..."
echo "=================================================="
cleanup_on_exit() {
    pkill -P $$ 2>/dev/null || true
}
trap cleanup_on_exit EXIT INT TERM
"$VENV_PYTHON" "$DIR/main.py"

