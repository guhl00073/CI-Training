#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# CI-Hörtrainer – Lokales Build-Script (macOS / Linux)
# Baut eine eigenständige .app (macOS) oder Binary (Linux) ohne Python-Requirement.
#
# Verwendung:
#   chmod +x build_local.sh
#   ./build_local.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        CI-Hörtrainer – Lokaler Build                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Voraussetzungen prüfen ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "❌ Kein .venv gefunden. Bitte zuerst: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

PYTHON=".venv/bin/python3"
PIP=".venv/bin/pip"

# ── PyInstaller installieren ──────────────────────────────────────────────────
echo "📦 Installiere PyInstaller …"
$PIP install --quiet "pyinstaller==6.10.0"

# ── Verzeichnisse sicherstellen ───────────────────────────────────────────────
mkdir -p data models docs/images

# ── Build ─────────────────────────────────────────────────────────────────────
echo ""
echo "🔨 Baue Executable …"
$PYTHON -m PyInstaller ci_trainer.spec --clean --noconfirm

# ── Ergebnis ──────────────────────────────────────────────────────────────────
echo ""
if [[ "$(uname)" == "Darwin" ]]; then
  APP="dist/CI-Hörtrainer.app"
  if [ -d "$APP" ]; then
    echo "✅ Build erfolgreich!"

    # ── macOS Launcher Script einrichten (verhindert LaunchServices-Absturz) ──
    MACOS_DIR="$APP/Contents/MacOS"
    if [ -f "$MACOS_DIR/CI-Hörtrainer" ] && [ ! -f "$MACOS_DIR/CI-Hörtrainer-bin" ]; then
      mv "$MACOS_DIR/CI-Hörtrainer" "$MACOS_DIR/CI-Hörtrainer-bin"
      cat << 'EOF' > "$MACOS_DIR/CI-Hörtrainer"
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$DIR/../Resources:$PYTHONPATH"
cd "$DIR/../Resources"
exec "$DIR/CI-Hörtrainer-bin" "$@"
EOF
      chmod +x "$MACOS_DIR/CI-Hörtrainer" "$MACOS_DIR/CI-Hörtrainer-bin"
    fi

    # ── Quarantine entfernen + Ad-hoc signieren via Python Helper ────────
    $PYTHON scripts/sign_mac_app.py "$APP"

    # ── LaunchServices Icon Cache aktualisieren ──────────────────────────
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true
    touch "$APP"
    killall Finder 2>/dev/null || true

    echo ""
    echo "   📁 App:      $SCRIPT_DIR/$APP"
    echo "   🚀 Starten:  open '$SCRIPT_DIR/$APP'"
    echo ""
    echo "Direkt starten? (j/n)"
    read -r answer
    if [[ "$answer" == "j" || "$answer" == "J" ]]; then
      open "$APP"
    fi
  else
    echo "❌ Build fehlgeschlagen – $APP nicht gefunden."
    exit 1
  fi
else
  BIN="dist/CI-Hörtrainer/CI-Hörtrainer"
  if [ -f "$BIN" ]; then
    echo "✅ Build erfolgreich!"
    echo ""
    echo "   📁 Binary:   $SCRIPT_DIR/$BIN"
    echo "   🚀 Starten:  $SCRIPT_DIR/$BIN"
    echo ""
    echo "Direkt starten? (j/n)"
    read -r answer
    if [[ "$answer" == "j" || "$answer" == "J" ]]; then
      "$BIN" &
    fi
  else
    echo "❌ Build fehlgeschlagen – $BIN nicht gefunden."
    exit 1
  fi
fi
