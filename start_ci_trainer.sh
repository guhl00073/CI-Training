#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================="
echo "🚀 Starte CI-Hörtrainer"
echo "======================================================="

# Pfad für Homebrew auf macOS ergänzen (Apple Silicon / Intel), falls nicht im PATH
if [ -x "/opt/homebrew/bin/brew" ]; then
    export PATH="/opt/homebrew/bin:$PATH"
elif [ -x "/usr/local/bin/brew" ]; then
    export PATH="/usr/local/bin:$PATH"
fi

# 1. Prüfen, ob Python 3 / Python installiert ist (sonst via Homebrew installieren)
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "⚠️ Python ist auf diesem System noch nicht installiert."
    if command -v brew &>/dev/null; then
        echo "🍺 Homebrew wurde gefunden. Installiere Python via Homebrew..."
        brew install python
        if command -v python3 &>/dev/null; then
            PYTHON_BIN="python3"
        elif command -v python &>/dev/null; then
            PYTHON_BIN="python"
        else
            echo "❌ Fehler: Python konnte via Homebrew nicht installiert werden."
            exit 1
        fi
    else
        echo "🍺 Homebrew ist ebenfalls nicht installiert. Versuche Homebrew & Python zu installieren..."
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
            echo "❌ Fehler: Neither Python 3 nor Homebrew could be installed automatically."
            echo "Bitte installieren Sie Python 3 (https://www.python.org/) oder Homebrew (https://brew.sh/)."
            exit 1
        fi
    fi
fi

echo "✓ Python gefunden: $($PYTHON_BIN --version)"

# 2. Prüfen, ob eine virtuelle Umgebung (.venv) existiert (und ggf. erstellen)
VENV_DIR="$DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️ Keine virtuelle Umgebung (.venv) gefunden. Erstelle eine neue .venv..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    if [ $? -eq 0 ]; then
        echo "✓ Virtuelle Umgebung (.venv) erfolgreich erstellt."
    else
        echo "❌ Fehler beim Erstellen der virtuellen Umgebung (.venv)."
        exit 1
    fi
else
    echo "✓ Virtuelle Umgebung (.venv) vorhanden."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Fehler: Python Executable in $VENV_DIR nicht gefunden."
    exit 1
fi

# 3. Prüfen und Installieren der erforderlichen Pakete via requirements.txt
REQUIREMENTS_FILE="$DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "📦 Überprüfe und installiere Abhängigkeiten aus requirements.txt..."
    "$VENV_PIP" install -r "$REQUIREMENTS_FILE" --quiet || echo "⚠️ Hinweis: Abhängigkeiten konnten nicht direkt installiert werden (z. B. offline)."
    echo "✓ Abhängigkeitsprüfung abgeschlossen."
else
    echo "⚠️ Warnung: requirements.txt wurde nicht gefunden!"
fi

# 4. Hauptanwendung starten
echo "======================================================="
echo "▶️ Starte Hauptanwendung..."
echo "======================================================="
"$VENV_PYTHON" "$DIR/main.py"
