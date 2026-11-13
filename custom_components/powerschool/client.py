"""PowerSchool client wrapper — normal import of client_body."""
from __future__ import annotations

from .client_body import PowerSchoolClient as _PowerSchoolClientImpl


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
    """Thin wrapper: roster cleanup after scrape; implementation lives in client_body."""

    def __init__(self, *args, **kwargs):
        self._impl = _PowerSchoolClientImpl(*args, **kwargs)

    def fetch_students(self, selected=None):
        return _clean_result(self._impl.fetch_students(selected))

    def __getattr__(self, name):
        return getattr(self._impl, name)
