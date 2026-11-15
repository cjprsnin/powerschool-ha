#!/usr/bin/env python3
"""Write option-1 notebook brand icons (embedded PNG, pure black).

Run from repo root:
  python3 scripts/install_brand_icons.py
  git add icon.png logo.png brand custom_components/powerschool
  git commit -m 'Brand: option 1 notebook icon'
  git push origin main
"""
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parents[1]
# PLACEHOLDER - replaced below in next commit if needed
IMG = None

# Load embedded image from same file's data section
_DATA = Path(__file__).with_name("brand_icon.b64")
if _DATA.exists():
    IMG = base64.b64decode(_DATA.read_text().strip())
else:
    raise SystemExit(
        "Missing scripts/brand_icon.b64 — pull latest main and retry."
    )

for rel in [
    "icon.png",
    "logo.png",
    "custom_components/powerschool/icon.png",
    "custom_components/powerschool/logo.png",
    "custom_components/powerschool/brand/icon.png",
    "custom_components/powerschool/brand/logo.png",
    "brand/icon.png",
    "brand/logo.png",
]:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(IMG)
    print(f"wrote {rel} ({len(IMG)} bytes)")
print("Done. git add + commit + push the PNG files.")
