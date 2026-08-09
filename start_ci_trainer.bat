@echo off
setlocal enabledelayedexpansion
echo =======================================================
echo 🚀 Starte CI-Hörtrainer (Windows)
echo =======================================================
cd /d "%~dp0"

:: 1. Prüfen, ob Python installiert ist
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Fehler: Python ist auf diesem System nicht installiert!
    echo Bitte installieren Sie Python 3 von https://www.python.org/
    pause
    exit /b 1
)

echo ✓ Python gefunden.
python --version

:: 2. Prüfen, ob virtuelle Umgebung (.venv) existiert (und ggf. erstellen)
if not exist ".venv" (
    echo ⚠️ Keine virtuelle Umgebung (.venv) gefunden. Erstelle .venv...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Fehler beim Erstellen der virtuellen Umgebung (.venv).
        pause
        exit /b 1
    )
    echo ✓ Virtuelle Umgebung (.venv) erfolgreich erstellt.
) else (
    echo ✓ Virtuelle Umgebung (.venv) vorhanden.
)

set VENV_PYTHON=.venv\Scripts\python.exe
set VENV_PIP=.venv\Scripts\pip.exe

:: 3. Requirements.txt prüfen und installieren
if exist "requirements.txt" (
    echo 📦 Überprüfe und installiere Abhängigkeiten aus requirements.txt...
    %VENV_PIP% install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo ⚠️ Hinweis: Einige Pakete konnten nicht installiert werden ^(z. B. offline^).
    ) else (
        echo ✓ Abhängigkeiten installiert.
    )
) else (
    echo ⚠️ Warnung: requirements.txt wurde nicht gefunden!
)

:: 4. Anwendung starten
echo =======================================================
echo ▶️ Starte CI-Hörtrainer...
echo =======================================================
%VENV_PYTHON% main.py
pause
