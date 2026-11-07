"""PowerSchool client — loads plain client_body.py."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent
_body = _DIR / "client_body.py"

if not _body.exists():
    raise ImportError(
        "PowerSchool client source missing: custom_components/powerschool/client_body.py"
    )

_code = _body.read_text(encoding="utf-8")
exec(compile(_code, str(_body), "exec"), globals())

if "PowerSchoolClient" not in globals():
    raise ImportError("PowerSchoolClient not defined after loading client_body.py")

__all__ = ["PowerSchoolClient"]
