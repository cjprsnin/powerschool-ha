"""PowerSchool client — loads from _client_gz_*.txt parts (known-good)."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_DIR = Path(__file__).parent
_parts = []
_i = 0
while True:
    p = _DIR / f"_client_gz_{_i}.txt"
    if not p.exists():
        break
    _parts.append(p.read_text().strip())
    _i += 1

if not _parts:
    raise ImportError("PowerSchool client payload missing (_client_gz_*.txt)")

_code = gzip.decompress(base64.b64decode("".join(_parts))).decode("utf-8")
exec(compile(_code, str(_DIR / "client_impl.py"), "exec"), globals())

__all__ = ["PowerSchoolClient"]
