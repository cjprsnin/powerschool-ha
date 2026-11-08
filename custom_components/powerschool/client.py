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


def _filter_roster(roster: list | None) -> list:
    """Drop lunch/recess/staff rows so Hearth and cards get instructional classes only."""
    out = []
    for row in roster or []:
        if not isinstance(row, dict):
            continue
        course = str(row.get("course") or "").lower()
        teacher = str(row.get("teacher") or "").lower()
        if "lunch" in course or "recess" in course:
            continue
        if teacher in ("staff, staff", "staff staff", "staff"):
            continue
        out.append(row)
    return out


def _clean_result(result):
    """Normalize student payloads after scrape."""
    if not isinstance(result, dict):
        return result
    students = result.get("students")
    if not isinstance(students, dict):
        return result
    for _name, student in students.items():
        if not isinstance(student, dict):
            continue
        if "class_roster" in student:
            filtered = _filter_roster(student.get("class_roster"))
            student["class_roster"] = filtered
            student["class_roster_count"] = len(filtered)
    return result


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
        return _clean_result(self._get_impl().fetch_students(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._get_impl(), name)


__all__ = ["PowerSchoolClient"]
