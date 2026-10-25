"""PowerSchool client — two-part embedded gzip."""
from __future__ import annotations
import base64, gzip
from pathlib import Path
_DIR = Path(__file__).parent
_a = (_DIR / "_ps_b64_a.txt").read_text().strip()
_b = (_DIR / "_ps_b64_b.txt").read_text().strip()
_code = gzip.decompress(base64.b64decode(_a + _b)).decode("utf-8")
exec(compile(_code, "client_impl.py", "exec"), globals())
__all__ = ["PowerSchoolClient"]
