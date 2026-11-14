#!/usr/bin/env python3
"""Install HACS/Marketplace brand icons into the integration package.

HA 2026.3+ Marketplace/HACS looks for:
  custom_components/<domain>/brand/icon.png
  custom_components/<domain>/brand/logo.png  (optional)

Root-level icon.png/logo.png alone are not enough for the Marketplace tile
("icon not available"). This copies the validated root PNGs into brand/.
"""
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "powerschool" / "brand"
BRAND.mkdir(parents=True, exist_ok=True)
ROOT_BRAND = ROOT / "brand"
ROOT_BRAND.mkdir(parents=True, exist_ok=True)

def load_png(name: str) -> bytes:
    local = ROOT / name
    if local.is_file() and local.stat().st_size > 100:
        data = local.read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return data
    url = f"https://raw.githubusercontent.com/cjprsnin/powerschool-ha/main/{name}"
    data = urllib.request.urlopen(url).read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{name} is not a valid PNG ({len(data)} bytes)")
    return data

icon = load_png("icon.png")
logo = load_png("logo.png")
for dest in (BRAND, ROOT_BRAND):
    (dest / "icon.png").write_bytes(icon)
    (dest / "logo.png").write_bytes(logo)
    print("wrote", dest / "icon.png", len(icon), "bytes")
print("Done. Commit brand/ folders and push, then Marketplace update.")
