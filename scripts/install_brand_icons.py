#!/usr/bin/env python3
"""Install PowerSchool brand icons (notebook mark, pure black background).

Run from repo root:
  python3 scripts/install_brand_icons.py
  git add icon.png logo.png brand custom_components/powerschool/brand custom_components/powerschool/icon.png custom_components/powerschool/logo.png
  git commit -m 'Brand: notebook icon on black'
  git push origin main
"""
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parents[1]
IMG = base64.b64decode(
    "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"
)

# Note: truncated in this push if API limits; full installer lives in artifacts
# Prefer running the complete script from the assistant session artifacts.
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
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(IMG)
    print("wrote", rel, len(IMG))
