#!/bin/bash
# CI-Hörtrainer macOS Double-Clickable Executable Launcher

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "   👂 Starte CI-Hörtrainer..."
echo "=================================================="

if [ -f "$DIR/.venv/bin/python" ]; then
    "$DIR/.venv/bin/python" "$DIR/main.py"
else
    python3 "$DIR/main.py"
fi
