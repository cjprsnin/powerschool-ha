"""Assemble the PowerSchool client from gzip+base64 parts shipped beside this file."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_parts: list[str] = []
_i = 0
while True:
    _p = _DIR / f"_client_gz_{_i}.txt"
    if not _p.exists():
        break
    _parts.append(_p.read_text(encoding="utf-8").strip())
    _i += 1
if not _parts:
    raise RuntimeError("PowerSchool client parts (_client_gz_*.txt) are missing")

_code = gzip.decompress(base64.b64decode("".join(_parts))).decode("utf-8")
_ns: dict = {"__name__": __name__, "__file__": str(_DIR / "client_impl.py")}
exec(_code, _ns)

# Re-export public symbols used by the integration
PowerSchoolClient = _ns["PowerSchoolClient"]
for _k, _v in _ns.items():
    if _k.startswith("_"):
        continue
    globals()[_k] = _v
