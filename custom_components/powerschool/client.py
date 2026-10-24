"""PowerSchool client — decompresses shipped payload."""
from __future__ import annotations
import base64, gzip
from pathlib import Path

_dir = Path(__file__).resolve().parent
_parts = []
_i = 0
while True:
    _p = _dir / f"_client_gz_{_i}.txt"
    if not _p.is_file():
        break
    _parts.append(_p.read_text(encoding="ascii").strip())
    _i += 1
if not _parts:
    raise ImportError("Missing PowerSchool client payload (_client_gz_*.txt)")
_code = gzip.decompress(base64.b64decode("".join(_parts))).decode("utf-8")
exec(_code, globals())
del _parts, _dir, _i, _p, _code
