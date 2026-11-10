#!/usr/bin/env python3
"""Improve parse_schedule (matrix-friendly) and parse_bulletin (more shapes)."""
from __future__ import annotations
import base64, json, sys
from pathlib import Path

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text(encoding="utf-8")
if "Matrix-style: no period cell" in code:
    print("schedule/bulletin parsers already patched")
    sys.exit(0)

# Payload is generated offline; functions replace parse_schedule / parse_bulletin.
_B64 = open(__file__).read()  # will be replaced
