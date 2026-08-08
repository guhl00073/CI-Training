#!/usr/bin/env bash
echo "======================================================="
echo "🚀 Starte CI-Hörtrainer (Linux)"
echo "======================================================="
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"
if [ -f "$DIR/.venv/bin/python" ]; then
    "$DIR/.venv/bin/python" main.py
else
    python3 main.py
fi
