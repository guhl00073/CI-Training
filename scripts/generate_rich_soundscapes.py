import wave
import struct
import math
import random
import os

SAMPLE_RATE = 44100
DURATION = 30  # seconds

def write_wav(filename, samples):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with wave.open(filename, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        
        max_val = max(abs(s) for s in samples) or 1.0
        norm_factor = 0.75 / max_val
        
        data = bytearray()
        for s in samples:
            val = int(s * norm_factor * 32767)
            val = max(-32768, min(32767, val))
            data.extend(struct.pack('<h', val))
        wav.writeframes(data)
    print(f"✓ Erstellt: {filename} ({os.path.getsize(filename)} bytes)")

def generate_restaurant(filename="data/ambient_restaurant.wav"):
    """Cafe & Restaurant: Glass clinks, cutlery clicks, warm room murmur."""
    total_samples = SAMPLE_RATE * DURATION
    buf = [0.0] * total_samples

    for i in range(total_samples):
        t = i / SAMPLE_RATE
        murmur = math.sin(2 * math.pi * 180 * t) * 0.1 + math.sin(2 * math.pi * 320 * t) * 0.08
        murmur += (random.random() - 0.5) * 0.15
        buf[i] = murmur

    # Add cutlery & glass clinks to buffer
    for i in range(total_samples):
        if random.random() < 0.0005:  # Glass/cup clink event
            freq = random.choice([2800, 3400, 4100, 4800])
            clink_dur = int(0.06 * SAMPLE_RATE)
            for k in range(clink_dur):
                if i + k < total_samples:
                    env = math.exp(-k / (SAMPLE_RATE * 0.012))
                    buf[i + k] += math.sin(2 * math.pi * freq * (k / SAMPLE_RATE)) * env * 0.45

    write_wav(filename, buf)

def generate_station(filename="data/ambient_station.wav"):
    """Bahnhof: Deep train hum + station PA gong/chime (Ding-Dong!)."""
    total_samples = SAMPLE_RATE * DURATION
    buf = [0.0] * total_samples

    for i in range(total_samples):
        t = i / SAMPLE_RATE
        hum = math.sin(2 * math.pi * 85 * t) * 0.25 + math.sin(2 * math.pi * 170 * t) * 0.15
        rumble = (random.random() - 0.5) * 0.2
        buf[i] = hum + rumble

    # Add Gong/Chime announcement chimes every 8 seconds (Ding-Dong!)
    for chime_time in [2.0, 10.0, 18.0, 26.0]:
        start_idx = int(chime_time * SAMPLE_RATE)
        # Ding (523 Hz - C5)
        dur = int(0.8 * SAMPLE_RATE)
        for k in range(dur):
            if start_idx + k < total_samples:
                env = math.exp(-k / (SAMPLE_RATE * 0.2))
                buf[start_idx + k] += math.sin(2 * math.pi * 523 * (k / SAMPLE_RATE)) * env * 0.6
        
        # Dong (659 Hz - E5) after 0.35s
        start_idx2 = start_idx + int(0.35 * SAMPLE_RATE)
        for k in range(dur):
            if start_idx2 + k < total_samples:
                env = math.exp(-k / (SAMPLE_RATE * 0.25))
                buf[start_idx2 + k] += math.sin(2 * math.pi * 659 * (k / SAMPLE_RATE)) * env * 0.6

    write_wav(filename, buf)

def generate_chatter(filename="data/ambient_chatter.wav"):
    """Stimmengewirr (Conversations / Babble): Multi-pitch vocal formants."""
    total_samples = SAMPLE_RATE * DURATION
    buf = [0.0] * total_samples

    for i in range(total_samples):
        t = i / SAMPLE_RATE
        cadence1 = 0.5 + 0.5 * math.sin(2 * math.pi * 3.5 * t)
        v1 = (math.sin(2 * math.pi * 130 * t) + 0.5 * math.sin(2 * math.pi * 390 * t)) * cadence1 * 0.25
        
        cadence2 = 0.5 + 0.5 * math.sin(2 * math.pi * 4.2 * t + 1.0)
        v2 = (math.sin(2 * math.pi * 240 * t) + 0.5 * math.sin(2 * math.pi * 720 * t)) * cadence2 * 0.25

        cadence3 = 0.5 + 0.5 * math.sin(2 * math.pi * 2.8 * t + 2.0)
        v3 = (math.sin(2 * math.pi * 180 * t) + 0.5 * math.sin(2 * math.pi * 540 * t)) * cadence3 * 0.2

        fricative = (random.random() - 0.5) * 0.12 * (cadence1 + cadence2)
        buf[i] = v1 + v2 + v3 + fricative

    write_wav(filename, buf)

def generate_traffic(filename="data/ambient_traffic.wav"):
    """Straßenverkehr: Passing car swooshes (Doppler effect) + tire rolling noise."""
    total_samples = SAMPLE_RATE * DURATION
    buf = [0.0] * total_samples

    for i in range(total_samples):
        t = i / SAMPLE_RATE
        road = (random.random() - 0.5) * 0.12
        engine_idle = math.sin(2 * math.pi * 60 * t) * 0.1
        buf[i] = road + engine_idle

    # Add passing cars every 5-6 seconds with Doppler swoosh
    car_times = [2.5, 8.5, 14.5, 20.5, 26.5]
    for c_time in car_times:
        start_idx = int(c_time * SAMPLE_RATE)
        pass_dur = int(3.5 * SAMPLE_RATE)
        for k in range(pass_dur):
            if start_idx + k < total_samples:
                progress = k / pass_dur  # 0 to 1
                freq = 380 - progress * 240
                vol_env = math.sin(math.pi * progress) * 0.5
                swoosh = math.sin(2 * math.pi * freq * (k / SAMPLE_RATE)) * vol_env
                buf[start_idx + k] += swoosh

    write_wav(filename, buf)

if __name__ == "__main__":
    generate_restaurant()
    generate_station()
    generate_chatter()
    generate_traffic()
    print("🚀 Alle 4 Umgebungs-Audiodateien wurden neu mit charakteristischen Sounds erzeugt!")
