"""PowerSchool client — plain multi-part source (_body_*.py)."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent

_parts = []
_i = 0
while True:
    p = _DIR / f"_body_{_i}.py"
    if not p.exists():
        break
    _parts.append(p.read_text(encoding="utf-8"))
    _i += 1

if not _parts:
    raise ImportError(
        "PowerSchool client source missing. Expected _body_0.py, _body_1.py, ..."
    )

_code = "".join(_parts)
exec(compile(_code, str(_DIR / "_body_0.py"), "exec"), globals())

if "PowerSchoolClient" not in globals():
    raise ImportError("PowerSchoolClient not defined after loading _body_*.py")

__all__ = ["PowerSchoolClient"]
