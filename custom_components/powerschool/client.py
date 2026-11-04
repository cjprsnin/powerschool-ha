"""PowerSchool client — prefer plain client_body.py, else gzip parts."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_DIR = Path(__file__).parent

_body = _DIR / "client_body.py"
if _body.exists():
    _code = _body.read_text(encoding="utf-8")
    exec(compile(_code, str(_body), "exec"), globals())
else:
    _parts = []
    _i = 0
    while True:
        p = _DIR / f"_client_gz_{_i}.txt"
        if not p.exists():
            break
        _parts.append(p.read_text().strip())
        _i += 1
    if not _parts:
        raise ImportError(
            "PowerSchool client payload missing (client_body.py or _client_gz_*.txt)"
        )
    _code = gzip.decompress(base64.b64decode("".join(_parts))).decode("utf-8")
    exec(compile(_code, str(_DIR / "client_impl.py"), "exec"), globals())

if "PowerSchoolClient" not in globals():
    raise ImportError("PowerSchoolClient not defined after loading client source")

__all__ = ["PowerSchoolClient"]
