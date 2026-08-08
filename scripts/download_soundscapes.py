#!/usr/bin/env python3
"""
download_soundscapes.py
───────────────────────
Lädt lizenzfreie Realaudio-Störgeräusche (CC0 / Public Domain) herunter 
und konvertiert sie automatisch in das benötigte WAV-Format für data/ambient_*.wav.

Verwendung im Terminal:
    python3 scripts/download_soundscapes.py
"""

import os
import sys
import subprocess
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Empfohlene freie Audioquellen (Wikimedia Commons CC0 Feldaufnahmen)
SOUND_SOURCES = {
    "station": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/41/Union_Station_Bay_Concourse_Ambience_%28Freesound%29.ogg",
        "output": os.path.join(DATA_DIR, "ambient_station.wav"),
        "label": "Bahnhof Hallen-Geräusche (Station)"
    },
    "traffic": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/77/Citystreet3.mp3",
        "output": os.path.join(DATA_DIR, "ambient_traffic.wav"),
        "label": "Stadtverkehr & Straßenlärm (Traffic)"
    }
}

def download_file(url: str, target_path: str):
    print(f"📥 Lade herunter: {url} ...")
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    temp_download = target_path + ".tmp"
    with urllib.request.urlopen(req) as response, open(temp_download, "wb") as out_file:
        out_file.write(response.read())
    return temp_download

def convert_to_wav(source_path: str, target_wav: str):
    print(f"🎵 Konvertiere nach {os.path.basename(target_wav)}...")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", source_path,
        "-ar", "44100", "-ac", "2", target_wav
    ]
    res = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0:
        print(f"  ✓ Erfolgreich erstellt: {target_wav}")
        if os.path.exists(source_path):
            os.remove(source_path)
    else:
        print(f"  ⚠️ Fehler bei ffmpeg Konvertierung.")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=======================================================")
    print("  CI-Hörtrainer - Störgeräusche Download & Konvertierung")
    print("=======================================================\n")
    
    for key, info in SOUND_SOURCES.items():
        print(f"➜ {info['label']}")
        try:
            tmp_file = download_file(info["url"], info["output"])
            convert_to_wav(tmp_file, info["output"])
        except Exception as e:
            print(f"  ⚠️ Download fehlgeschlagen: {e}")

if __name__ == "__main__":
    main()
