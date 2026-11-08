"""PowerSchool client — loads plain client_body.py (hot-reload on file change)."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent
_body = _DIR / "client_body.py"
_mtime: float | None = None
_impl_cls = None


def _load_cls():
    """Load/reload PowerSchoolClient from client_body.py when the file changes."""
    global _mtime, _impl_cls
    if not _body.exists():
        raise ImportError(
            "PowerSchool client source missing: custom_components/powerschool/client_body.py"
        )
    mtime = _body.stat().st_mtime
    if _impl_cls is not None and _mtime == mtime:
        return _impl_cls
    code = _body.read_text(encoding="utf-8")
    ns: dict = {"__name__": "powerschool_client_body"}
    exec(compile(code, str(_body), "exec"), ns)
    cls = ns.get("PowerSchoolClient")
    if cls is None:
        raise ImportError("PowerSchoolClient not defined after loading client_body.py")
    _impl_cls = cls
    _mtime = mtime
    return cls


class PowerSchoolClient:
    """Stable wrapper that rebuilds the real client when client_body.py changes."""

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._impl = None
        self._impl_mtime: float | None = None

    def _get_impl(self):
        cls = _load_cls()
        if self._impl is None or self._impl_mtime != _mtime:
            self._impl = cls(*self._args, **self._kwargs)
            self._impl_mtime = _mtime
        return self._impl

    def fetch_students(self, *args, **kwargs):
        return self._get_impl().fetch_students(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._get_impl(), name)


__all__ = ["PowerSchoolClient"]
