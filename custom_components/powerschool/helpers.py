"""Shared helpers for PowerSchool integration."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    DUE_SOON_DAYS,
    GRADE_HISTORY_MAX,
    TREND_THRESHOLD,
    UPCOMING_DAYS,
)


def parse_due(value: Any) -> date | None:
    """Parse a due date/datetime into a date."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    s = str(value).strip()
    if not s:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ):
        try:
            return datetime.strptime(s[:26], fmt).date()
        except ValueError:
            continue

    try:
        dt = dt_util.parse_datetime(s)
        if dt:
            if dt.tzinfo:
                return dt_util.as_local(dt).date()
            return dt.date()
    except Exception:
        pass
    return None


def days_until(due: date, today: date | None = None) -> int:
    today = today or dt_util.now().date()
    return (due - today).days


def is_ungraded(assignment: dict) -> bool:
    """True when the assignment has no score yet."""
    if assignment.get("percent") is not None:
        return False
    if assignment.get("letter"):
        return False
    # Some portals populate earned/possible only after grading
    if assignment.get("earned") is not None and assignment.get("possible") is not None:
        return False
    return True


def collect_upcoming(
    student: dict,
    soon_days: int = DUE_SOON_DAYS,
    upcoming_days: int = UPCOMING_DAYS,
) -> tuple[list[dict], list[dict]]:
    """Return (due_soon_list, upcoming_list) of ungraded assignments."""
    today = dt_util.now().date()
    due_soon: list[dict] = []
    upcoming: list[dict] = []

    for course in student.get("courses") or []:
        course_name = course.get("course") or "Course"
        section_id = course.get("section_id")

        for a in course.get("assignments") or []:
            if not is_ungraded(a):
                continue

            due = parse_due(a.get("due"))
            if due is None:
                continue

            delta = days_until(due, today)
            if delta < 0:
                continue  # past due — handled by missing/late logic

            item = {
                "name": a.get("name"),
                "course": course_name,
                "section_id": section_id,
                "due": due.isoformat(),
                "days_until_due": delta,
                "category": a.get("category"),
                "assignment_id": a.get("assignment_id"),
                "late": bool(a.get("late", False)),
                "missing": bool(a.get("missing", False)),
            }

            if delta <= soon_days:
                due_soon.append(item)
            if delta <= upcoming_days:
                upcoming.append(item)

    due_soon.sort(key=lambda x: x["days_until_due"])
    upcoming.sort(key=lambda x: x["days_until_due"])
    return due_soon, upcoming


def update_grade_history(
    history: list[dict] | None,
    current_percent: float | None,
    max_len: int = GRADE_HISTORY_MAX,
) -> tuple[list[dict], dict]:
    """
    Append current percent to a rolling history and compute delta/trend.
    Returns (new_history, attrs_dict).
    """
    history = list(history or [])
    now_iso = dt_util.utcnow().isoformat()

    if current_percent is not None:
        current_percent = float(current_percent)
        if not history or history[-1].get("percent") != current_percent:
            history.append({"percent": current_percent, "ts": now_iso})
        else:
            # Refresh timestamp on the latest point
            history[-1] = {"percent": current_percent, "ts": now_iso}

    if len(history) > max_len:
        history = history[-max_len:]

    attrs: dict[str, Any] = {
        "grade_history": history,
        "grade_history_points": [p["percent"] for p in history],
    }

    if not history:
        attrs.update(
            {
                "grade_delta": None,
                "grade_delta_recent": None,
                "grade_trend": "unknown",
                "previous_grade_percent": None,
            }
        )
        return history, attrs

    current = history[-1]["percent"]
    previous = history[-2]["percent"] if len(history) >= 2 else None
    oldest = history[0]["percent"]

    delta_recent = (current - previous) if previous is not None else None
    delta_window = (current - oldest) if len(history) >= 2 else None

    def _trend(delta: float | None) -> str:
        if delta is None:
            return "unknown"
        if delta >= TREND_THRESHOLD:
            return "up"
        if delta <= -TREND_THRESHOLD:
            return "down"
        return "stable"

    attrs.update(
        {
            "previous_grade_percent": previous,
            "grade_delta_recent": round(delta_recent, 2) if delta_recent is not None else None,
            "grade_delta": round(delta_window, 2) if delta_window is not None else None,
            "grade_trend": _trend(delta_window if delta_window is not None else delta_recent),
        }
    )
    return history, attrs
