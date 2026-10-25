"""PowerSchool client — joins _client_src_*.py parts."""
from __future__ import annotations
from pathlib import Path

_DIR = Path(__file__).parent
_parts = []
_i = 0
while True:
    p = _DIR / f"_client_src_{_i}.py"
    if not p.exists():
        break
    _parts.append(p.read_text())
    _i += 1
if not _parts:
    raise ImportError("PowerSchool client source parts missing (_client_src_*.py)")
_code = "".join(_parts)
exec(compile(_code, str(_DIR / "client_impl.py"), "exec"), globals())
__all__ = ["PowerSchoolClient"]
