"""PowerSchool client — assembled from split parts for repo upload."""
from __future__ import annotations
from pathlib import Path

_code = []
_dir = Path(__file__).resolve().parent
_i = 0
while True:
    _p = _dir / f"_client_part{_i}.txt"
    if not _p.is_file():
        break
    _code.append(_p.read_text(encoding="utf-8"))
    _i += 1
if not _code:
    raise ImportError("PowerSchool client parts missing (_client_part*.txt)")
exec("".join(_code), globals())
del _code, _dir, _i, _p
