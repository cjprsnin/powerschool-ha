"""PowerSchool client — plain multi-part source (no compression)."""
from __future__ import annotations
from pathlib import Path
_DIR = Path(__file__).parent
_parts = []
_i = 0
while True:
    p = _DIR / f"_src{_i}.py"
    if not p.exists():
        break
    _parts.append(p.read_text())
    _i += 1
if not _parts:
    raise ImportError("PowerSchool client source parts missing (_src*.py)")
_code = "".join(_parts)
exec(compile(_code, str(_DIR / "client_body.py"), "exec"), globals())
if "PowerSchoolClient" not in globals():
    raise ImportError("PowerSchoolClient not defined after loading source parts")
__all__ = ["PowerSchoolClient"]
