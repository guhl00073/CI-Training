#!/bin/bash
# CI-Hörtrainer macOS Double-Clickable Executable Launcher

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo "   👂 Starte CI-Hörtrainer..."
echo "=================================================="

python3 "$DIR/main.py"
