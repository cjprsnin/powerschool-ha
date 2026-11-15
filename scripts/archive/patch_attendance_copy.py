#!/usr/bin/env python3
"""Preserve absences/tardies when building per-course result dicts."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text()
old = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','section_id')}"
new = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','section_id','absences','tardies')}"
if old not in code:
    if "absences','tardies')" in code:
        print("Already patched")
        sys.exit(0)
    sys.exit("copy line not found")
code = code.replace(old, new, 1)
compile(code, "client_body.py", "exec")
path.write_text(code)
print("Patched", path)
