"""PowerSchool client — loads from _body_*.py parts, else gzip, else client_body.py."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_DIR = Path(__file__).parent


def _load_code() -> tuple[str, str]:
    # Prefer numbered plain parts (easier to push/update)
    parts = []
    i = 0
    while True:
        p = _DIR / f"_body_{i}.py"
        if not p.exists():
            break
        parts.append(p.read_text(encoding="utf-8"))
        i += 1
    if parts:
        return "".join(parts), str(_DIR / "_body_0.py")

    body = _DIR / "client_body.py"
    if body.exists():
        return body.read_text(encoding="utf-8"), str(body)

    gz_parts = []
    i = 0
    while True:
        p = _DIR / f"_client_gz_{i}.txt"
        if not p.exists():
            break
        gz_parts.append(p.read_text().strip())
        i += 1
    if gz_parts:
        code = gzip.decompress(base64.b64decode("".join(gz_parts))).decode("utf-8")
        return code, str(_DIR / "client_impl.py")

    raise ImportError(
        "PowerSchool client payload missing (_body_*.py, client_body.py, or _client_gz_*.txt)"
    )


_code, _origin = _load_code()
exec(compile(_code, _origin, "exec"), globals())

if "PowerSchoolClient" not in globals():
    raise ImportError("PowerSchoolClient not defined after loading client source")

__all__ = ["PowerSchoolClient"]
