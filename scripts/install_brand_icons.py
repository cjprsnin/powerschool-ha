#!/usr/bin/env python3
"""Install PowerSchool brand icons — option 1 notebook on pure black."""
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def make_icon(size: int) -> "Image.Image":
    bg = (0, 0, 0)
    gold = (201, 152, 40)
    white = (250, 250, 248)
    line = (35, 35, 38)
    hole = (20, 20, 22)
    base = 512
    img = Image.new("RGB", (base, base), bg)
    d = ImageDraw.Draw(img)
    cx = cy = base // 2
    r = 210
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=gold, width=12)
    d.rounded_rectangle([155, 145, 355, 375], radius=22, fill=white)
    d.rounded_rectangle([145, 145, 185, 375], radius=14, fill=gold)
    d.rectangle([170, 145, 185, 375], fill=gold)
    for y in (180, 230, 280, 330):
        d.ellipse([155, y, 175, y + 20], fill=hole)
    for y in (185, 230, 275):
        d.rounded_rectangle([205, y, 325, y + 14], radius=5, fill=line)
    pts = [(215, 350), (250, 325), (280, 335), (320, 285)]
    d.line(pts, fill=gold, width=10, joint="curve")
    d.polygon([(320, 285), (298, 292), (310, 310)], fill=gold)
    d.line([(285, 355), (300, 370), (340, 325)], fill=gold, width=9, joint="curve")
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    px = out.load()
    for y in range(size):
        for x in range(size):
            r, g, b = px[x, y]
            if r < 20 and g < 20 and b < 20:
                px[x, y] = (0, 0, 0)
    return out


icon = make_icon(256)
logo = make_icon(512)

for rel, im in [
    ("icon.png", icon),
    ("logo.png", logo),
    ("custom_components/powerschool/icon.png", icon),
    ("custom_components/powerschool/logo.png", logo),
    ("custom_components/powerschool/brand/icon.png", icon),
    ("custom_components/powerschool/brand/logo.png", logo),
    ("brand/icon.png", icon),
    ("brand/logo.png", logo),
]:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)
    print(f"wrote {rel}")
print("Done.")
