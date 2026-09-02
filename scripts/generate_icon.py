#!/usr/bin/env python3
"""
CI-Hörtrainer Icon Generator – Variante C (Petrol / Royal Gradient)
Isoliert das grafische Symbol, skaliert es auf 75% der Kachel und rendert
ein scharfes macOS Squircle Icon mit Petrol/Navy-Verlauf und Glow.
"""

import math
import subprocess
import pathlib
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = pathlib.Path("/Users/gerald/.gemini/antigravity-ide/brain/29ae107e-15f8-4901-856b-a35f461ad050/.user_uploaded/media_1787845804575.png")
OUT = pathlib.Path("docs/iconset")
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 1024
CORNER_RADIUS = int(SIZE * 0.225)  # Apple standard macOS squircle corner radius

def generate_variant_c():
    img_orig = Image.open(SRC).convert("RGBA")
    arr = np.array(img_orig)

    # 1. Grafisches Symbol isolieren (ohne Text)
    mask = (arr[:,:,0] < 245) | (arr[:,:,1] < 245) | (arr[:,:,2] < 245)
    symbol_mask = mask.copy()
    symbol_mask[400:, :] = False  # Text ausschließen
    coords = np.argwhere(symbol_mask)
    sy0, sx0 = coords.min(axis=0)
    sy1, sx1 = coords.max(axis=0) + 1

    symbol_crop = img_orig.crop((sx0, sy0, sx1, sy1))

    # 2. Transparenten Alphakanal mit weichem Antialiasing erzeugen
    arr_s = np.array(symbol_crop, dtype=float)
    lum = 0.299 * arr_s[:,:,0] + 0.587 * arr_s[:,:,1] + 0.114 * arr_s[:,:,2]
    alpha = np.clip((252 - lum) / 25.0 * 255.0, 0, 255)
    alpha_norm = np.maximum(alpha / 255.0, 1e-4)

    r = np.clip((arr_s[:,:,0] - 255 * (1 - alpha_norm)) / alpha_norm, 0, 255)
    g = np.clip((arr_s[:,:,1] - 255 * (1 - alpha_norm)) / alpha_norm, 0, 255)
    b = np.clip((arr_s[:,:,2] - 255 * (1 - alpha_norm)) / alpha_norm, 0, 255)

    res = np.zeros_like(arr_s, dtype=np.uint8)
    res[:,:,0] = r.astype(np.uint8)
    res[:,:,1] = g.astype(np.uint8)
    res[:,:,2] = b.astype(np.uint8)
    res[:,:,3] = alpha.astype(np.uint8)
    symbol_trans = Image.fromarray(res, 'RGBA')

    # Leichte Helligkeitsanpassung für optimalen Pop auf dunklem Verlauf
    arr_trans = np.array(symbol_trans, dtype=float)
    arr_trans[:,:,:3] = np.clip(arr_trans[:,:,:3] * 1.25 + 15, 0, 255)
    sym_boosted = Image.fromarray(arr_trans.astype(np.uint8), 'RGBA')

    # 3. Squircle Maske
    squircle_mask = Image.new('L', (SIZE, SIZE), 0)
    draw_m = ImageDraw.Draw(squircle_mask)
    draw_m.rounded_rectangle([0, 0, SIZE-1, SIZE-1], radius=CORNER_RADIUS, fill=255)

    # 4. Hintergrund: Petrol / Royal Navy Verlauf
    bg = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 255))
    draw_c = ImageDraw.Draw(bg)
    for y in range(SIZE):
        for x in range(0, SIZE, 4):
            t = (x + (SIZE - y)) / (2 * SIZE)
            r_c = int(12 * (1-t) + 0 * t)
            g_c = int(24 * (1-t) + 75 * t)
            b_c = int(55 * (1-t) + 120 * t)
            draw_c.rectangle([x, y, x+3, y], fill=(r_c, g_c, b_c, 255))

    # 5. Symbol skalieren (auf 720px Breite, ca. 75% der Fläche)
    sym_w = 720
    sym_h = int(sym_w * (symbol_trans.height / symbol_trans.width))
    sym_scaled = sym_boosted.resize((sym_w, sym_h), Image.LANCZOS)
    sym_scaled = sym_scaled.filter(ImageFilter.UnsharpMask(radius=0.8, percent=80, threshold=2))

    sx = (SIZE - sym_w) // 2
    sy = (SIZE - sym_h) // 2

    # 6. Sanfter Glow um das Symbol
    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    glow.paste((0, 210, 200, 110), (sx, sy), sym_scaled.split()[3])
    glow = glow.filter(ImageFilter.GaussianBlur(24))

    final = Image.alpha_composite(bg, glow)
    final.paste(sym_scaled, (sx, sy), sym_scaled)
    final.putalpha(squircle_mask)

    # 7. Master PNG speichern
    master_png = OUT / "icon_1024.png"
    final.save(str(master_png), 'PNG', optimize=True)
    print(f"✓ Master: {master_png}")

    # 8. macOS Iconset erzeugen
    iconset = OUT / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for sz in sizes:
        resized = final.resize((sz, sz), Image.LANCZOS)
        if sz <= 32:
            resized = resized.filter(ImageFilter.UnsharpMask(radius=0.5, percent=120, threshold=1))
        resized.save(str(iconset / f"icon_{sz}x{sz}.png"), 'PNG')
        if sz <= 512:
            resized2 = final.resize((sz*2, sz*2), Image.LANCZOS)
            resized2.save(str(iconset / f"icon_{sz}x{sz}@2x.png"), 'PNG')

    # 9. iconutil -> .icns
    icns_out = OUT / "icon.icns"
    r = subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns_out)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✅ icon.icns ({icns_out.stat().st_size // 1024} KB)")
    else:
        print(f"❌ iconutil: {r.stderr}")

    # 10. Windows .ico
    ico_out = OUT / "icon.ico"
    frames = [final.resize((s, s), Image.LANCZOS).convert('RGBA') for s in [16, 32, 48, 64, 128, 256]]
    frames[0].save(str(ico_out), format='ICO', sizes=[(s,s) for s in [16,32,48,64,128,256]], append_images=frames[1:])
    print(f"✅ icon.ico ({ico_out.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    generate_variant_c()
