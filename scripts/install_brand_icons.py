#!/usr/bin/env python3
"""Install PowerSchool brand icons — option 1 notebook on pure black."""
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parents[1]
parts_dir = Path(__file__).resolve().parent / "brand_icon_parts"
b64 = "".join(p.read_text().strip() for p in sorted(parts_dir.glob("part*.txt"), key=lambda x: x.name))
IMG = base64.b64decode(b64)

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
print("Done.")
