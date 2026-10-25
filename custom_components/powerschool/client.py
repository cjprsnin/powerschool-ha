"""PowerSchool client — multi-part embedded gzip."""
from __future__ import annotations
import base64, gzip
from pathlib import Path
_DIR = Path(__file__).parent
_parts = []
_i = 0
while True:
    p = _DIR / f"_ps_p{_i}.txt"
    if not p.exists():
        break
    _parts.append(p.read_text().strip())
    _i += 1
if not _parts:
    raise ImportError("PowerSchool client payload parts missing (_ps_p*.txt)")
_code = gzip.decompress(base64.b64decode("".join(_parts))).decode("utf-8")
exec(compile(_code, "client_impl.py", "exec"), globals())
__all__ = ["PowerSchoolClient"]
