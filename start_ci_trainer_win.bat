@echo off
setlocal enabledelayedexpansion
echo =======================================================
echo Starte CI-Hoertrainer (Windows)
echo =======================================================
cd /d "%~dp0"

:: 1. Pruefen, ob Python installiert ist (sonst via winget installieren)
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNUNG] Python ist auf diesem System noch nicht installiert.
    where winget >nul 2>nul
    if !errorlevel! equ 0 (
        echo [INFO] winget ^(Windows Package Manager^) wurde gefunden. Installiere Python via winget...
        winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
        where python >nul 2>nul
        if !errorlevel! neq 0 (
            echo [FEHLER] Fehler: Python konnte nicht automatisch via winget installiert werden.
            echo Bitte starten Sie die Eingabeaufforderung neu oder installieren Sie Python von https://www.python.org/
            pause
            exit /b 1
        )
    ) else (
        echo [FEHLER] Fehler: Python ist auf diesem System nicht installiert!
        echo Bitte installieren Sie Python 3 von https://www.python.org/
        pause
        exit /b 1
    )
)

echo [OK] Python gefunden.
python --version

:: 2. Pruefen, ob virtuelle Umgebung (.venv) existiert (und ggf. erstellen)
if not exist ".venv" (
    echo [WARNUNG] Keine virtuelle Umgebung ^(.venv^) gefunden. Erstelle .venv...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [FEHLER] Fehler beim Erstellen der virtuellen Umgebung ^(.venv^).
        pause
        exit /b 1
    )
    echo [OK] Virtuelle Umgebung ^(.venv^) erfolgreich erstellt.
) else (
    echo [OK] Virtuelle Umgebung ^(.venv^) vorhanden.
)

set VENV_PYTHON=.venv\Scripts\python.exe
set VENV_PIP=.venv\Scripts\pip.exe

:: 3. Requirements.txt pruefen und installieren
if exist "requirements.txt" (
    echo [INFO] Ueberpruefe und installiere Abhaengigkeiten aus requirements.txt...
    %VENV_PIP% install -r requirements.txt --quiet
    if !errorlevel! neq 0 (
        echo [HINWEIS] Hinweis: Einige Pakete konnten nicht installiert werden ^(z. B. offline^).
    ) else (
        echo [OK] Abhaengigkeiten installiert.
    )
) else (
    echo [WARNUNG] Warnung: requirements.txt wurde nicht gefunden!
)

:: 4. Anwendung starten
echo =======================================================
echo Starte CI-Hoertrainer...
echo =======================================================
%VENV_PYTHON% main.py
pause
