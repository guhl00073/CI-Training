import os
import sys
import math
import wave
import struct
import random
import subprocess

SAMPLE_RATE = 44100
DURATION = 30  # seconds

def mix_wavs(wav_files, output_file, target_duration=30):
    """Mixes multiple WAV files together cleanly into a single stereo/mono WAV file."""
    buffers = []
    max_len = 0
    
    for wfile in wav_files:
        if not os.path.exists(wfile):
            continue
        try:
            with wave.open(wfile, 'rb') as w:
                nch = w.getnchannels()
                framerate = w.getframerate()
                nframes = w.getnframes()
                raw_data = w.readframes(nframes)
                
                # Convert raw 16-bit PCM bytes to floats
                samples = []
                for k in range(0, len(raw_data), 2 * nch):
                    val = struct.unpack('<h', raw_data[k:k+2])[0] / 32768.0
                    samples.append(val)
                
                # Resample or pad/loop to target_duration
                needed = int(SAMPLE_RATE * target_duration)
                if len(samples) < needed and len(samples) > 0:
                    # Loop
                    mult = (needed // len(samples)) + 1
                    samples = (samples * mult)[:needed]
                elif len(samples) > needed:
                    samples = samples[:needed]
                    
                buffers.append(samples)
                max_len = max(max_len, len(samples))
        except Exception as e:
            print(f"Error reading {wfile}: {e}")

    if not buffers:
        return

    target_samples = int(SAMPLE_RATE * target_duration)
    out_buf = [0.0] * target_samples

    for buf in buffers:
        for i in range(min(len(buf), target_samples)):
            out_buf[i] += buf[i]

    # Normalize to avoid clipping
    peak = max(abs(s) for s in out_buf) or 1.0
    norm = 0.85 / peak

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with wave.open(output_file, 'wb') as out_w:
        out_w.setnchannels(1)
        out_w.setsampwidth(2)
        out_w.setframerate(SAMPLE_RATE)
        
        raw_out = bytearray()
        for s in out_buf:
            val = int(s * norm * 32767)
            val = max(-32768, min(32767, val))
            raw_out.extend(struct.pack('<h', val))
        out_w.writeframes(raw_out)
        
    print(f"✓ Realistische Kulisse erstellt: {output_file} ({os.path.getsize(output_file)} bytes)")

def generate_voice_file(voice, text, outfile):
    """Generates a speech audio file using macOS native 'say' command."""
    os.makedirs(".cache/tts_temp", exist_ok=True)
    aiff_path = outfile.replace(".wav", ".aiff")
    cmd = ["say", "-v", voice, "-o", aiff_path, text]
    subprocess.run(cmd, check=True)
    
    # Convert AIFF to 44.1kHz 16-bit WAV
    cmd_conv = ["ffmpeg", "-y", "-i", aiff_path, "-ar", str(SAMPLE_RATE), "-ac", "1", outfile]
    subprocess.run(cmd_conv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if os.path.exists(aiff_path):
        os.remove(aiff_path)

def build_restaurant_ambiance(output_path="data/ambient_restaurant.wav"):
    """Generates real restaurant ambient soundscape with background conversation & clinks."""
    print("🔊 Generiere reale Café & Restaurant Kulisse...")
    phrases = [
        ("Grandpa (Deutsch (Deutschland))", "Könnten wir bitte zahlen? Vielen Dank."),
        ("Reed (Deutsch (Deutschland))", "Ich nehme gerne einen Espresso und ein stilles Wasser."),
        ("Rocko (Deutsch (Deutschland))", "Haben Sie noch einen freien Tisch im Außenbereich?"),
        ("Sandy (Deutsch (Deutschland))", "Das Essen schmeckt wirklich hervorragend heute Abend."),
        ("Shelley (Deutsch (Deutschland))", "Wir hätten gerne noch zwei Nachspeisen, bitte."),
        ("Grandpa (Deutsch (Deutschland))", "Die Rechnung geht zusammen, danke schön.")
    ]
    
    temp_files = []
    for idx, (voice, phrase) in enumerate(phrases):
        fpath = f".cache/tts_temp/rest_{idx}.wav"
        generate_voice_file(voice, phrase, fpath)
        temp_files.append(fpath)

    # Generate synthetic cutlery/glass clinks sound
    clink_file = ".cache/tts_temp/rest_clinks.wav"
    samples = [0.0] * (SAMPLE_RATE * DURATION)
    for i in range(len(samples)):
        if random.random() < 0.0004:
            freq = random.choice([2600, 3200, 3900, 4500])
            for k in range(int(0.08 * SAMPLE_RATE)):
                if i + k < len(samples):
                    env = math.exp(-k / (SAMPLE_RATE * 0.015))
                    samples[i + k] += math.sin(2 * math.pi * freq * (k / SAMPLE_RATE)) * env * 0.4
    
    # Write clinks wav
    with wave.open(clink_file, 'wb') as cw:
        cw.setnchannels(1)
        cw.setsampwidth(2)
        cw.setframerate(SAMPLE_RATE)
        raw_c = bytearray()
        for s in samples:
            val = int(s * 32767)
            raw_c.extend(struct.pack('<h', max(-32768, min(32767, val))))
        cw.writeframes(raw_c)
    temp_files.append(clink_file)

    mix_wavs(temp_files, output_path)

def build_station_ambiance(output_path="data/ambient_station.wav"):
    """Generates real railway station ambient soundscape with PA announcements."""
    print("🔊 Generiere reale Bahnhof & ÖPNV Kulisse...")
    announcements = [
        ("Shelley (Deutsch (Deutschland))", "Gleis 3. Einfahrt des Intercity Express 5 7 2 nach Frankfurt Hauptbahnhof über Kassel. Bitte Vorsicht an der Bahnsteigkante."),
        ("Reed (Deutsch (Deutschland))", "Achtung am Gleis 1. Die Abfahrt des Regionalexpress verzögert sich um wenige Minuten. Wir bitten um Ihr Verständnis.")
    ]
    
    temp_files = []
    for idx, (voice, text) in enumerate(announcements):
        fpath = f".cache/tts_temp/stat_{idx}.wav"
        generate_voice_file(voice, text, fpath)
        temp_files.append(fpath)

    # Generate train engine rumble
    rumble_file = ".cache/tts_temp/stat_rumble.wav"
    samples = [0.0] * (SAMPLE_RATE * DURATION)
    for i in range(len(samples)):
        t = i / SAMPLE_RATE
        r = math.sin(2 * math.pi * 75 * t) * 0.3 + math.sin(2 * math.pi * 140 * t) * 0.2
        samples[i] = r
    
    with wave.open(rumble_file, 'wb') as rw:
        rw.setnchannels(1)
        rw.setsampwidth(2)
        rw.setframerate(SAMPLE_RATE)
        raw_r = bytearray()
        for s in samples:
            val = int(s * 32767)
            raw_r.extend(struct.pack('<h', max(-32768, min(32767, val))))
        rw.writeframes(raw_r)
    temp_files.append(rumble_file)

    mix_wavs(temp_files, output_path)

def build_chatter_ambiance(output_path="data/ambient_chatter.wav"):
    """Generates real multi-speaker crowd babble chatter."""
    print("🔊 Generiere reale Stimmengewirr (Party/Babble) Kulisse...")
    texts = [
        ("Grandpa (Deutsch (Deutschland))", "Das war gestern wirklich ein interessanter Nachmittag im Park."),
        ("Reed (Deutsch (Deutschland))", "Hast du schon die aktuellen Nachrichten von heute morgen gelesen?"),
        ("Rocko (Deutsch (Deutschland))", "Wir wollen am Wochenende zusammen in die Berge fahren."),
        ("Sandy (Deutsch (Deutschland))", "Das Konzert am Freitagabend war absolut fantastisch und voller Energie."),
        ("Shelley (Deutsch (Deutschland))", "Morgen fange ich mit dem neuen Kurs an und freue mich schon darauf.")
    ]
    
    temp_files = []
    for idx, (voice, text) in enumerate(texts):
        fpath = f".cache/tts_temp/chat_{idx}.wav"
        generate_voice_file(voice, text, fpath)
        temp_files.append(fpath)

    mix_wavs(temp_files, output_path)

def build_traffic_ambiance(output_path="data/ambient_traffic.wav"):
    """Generates real city traffic rumble soundscape."""
    print("🔊 Generiere reale Straßenverkehrs-Kulisse...")
    samples = [0.0] * (SAMPLE_RATE * DURATION)
    for i in range(len(samples)):
        t = i / SAMPLE_RATE
        engine = math.sin(2 * math.pi * 60 * t) * 0.35 + math.sin(2 * math.pi * 120 * t) * 0.25
        samples[i] = engine

    # Add car pass-by Doppler sweep
    for pass_by_time in [5.0, 15.0, 24.0]:
        start_idx = int(pass_by_time * SAMPLE_RATE)
        dur = int(3.5 * SAMPLE_RATE)
        for k in range(dur):
            if start_idx + k < len(samples):
                progress = k / dur
                freq = 320 - progress * 140
                vol = math.sin(math.pi * progress) * 0.45
                samples[start_idx + k] += math.sin(2 * math.pi * freq * (k / SAMPLE_RATE)) * vol

    traffic_file = ".cache/tts_temp/traffic_gen.wav"
    with wave.open(traffic_file, 'wb') as tw:
        tw.setnchannels(1)
        tw.setsampwidth(2)
        tw.setframerate(SAMPLE_RATE)
        raw_t = bytearray()
        for s in samples:
            val = int(s * 32767)
            raw_t.extend(struct.pack('<h', max(-32768, min(32767, val))))
        tw.writeframes(raw_t)

    mix_wavs([traffic_file], output_path)

if __name__ == "__main__":
    build_restaurant_ambiance()
    build_station_ambiance()
    build_chatter_ambiance()
    build_traffic_ambiance()
    print("✨ Alle 4 realistischen Audio-Soundscapes wurden erfolgreich erzeugt!")
