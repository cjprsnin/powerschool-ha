"""PowerSchool HA client — thin adapter over modular scrape package."""
from __future__ import annotations

from http.cookiejar import CookieJar

from . import ps_http as S
from .ps_grades import current_school_year_range
from .ps_http import find_students, get, login, login_success
from .ps_assign import process_student


class PowerSchoolClient:
    """Home Assistant adapter around the tested PowerSchool protocol."""

    def __init__(
        self,
        base_url=None,
        username="",
        password="",
        term_start=None,
        term_end=None,
        photo_dir=None,
    ):
        self.base_url = (base_url or getattr(S, "BASE_URL", "") or "").rstrip("/")
        self.username = username
        self.password = password
        self.term_start = term_start or current_school_year_range()[0]
        self.term_end = term_end or current_school_year_range()[1]
        self.photo_dir = photo_dir
        S.BASE_URL = self.base_url
        S.PUBLIC_URL = self.base_url + "/public/"
        S.LOGIN_URL = self.base_url + "/guardian/home.html"
        S.HOME_URL = S.LOGIN_URL
        S.LOOKUP_URL = ""
        S.ACTIVE_TERM_START = self.term_start
        S.ACTIVE_TERM_END = self.term_end
        S.TIMEOUT = 30
        S.DELAY = 0.25
        S.GET_ASSIGNMENTS = True
        # Lazy opener: do not build SSL context on the event loop.
        S.jar = CookieJar()
        S.opener = None

    def _login_and_discover(self):
        r = login(self.username, self.password)
        if r["status"] in (401, 403) or not login_success(r):
            raise PermissionError("PowerSchool login failed")
        students = find_students(r["body"])
        if not students:
            home = get(S.HOME_URL)
            if home["status"] in (401, 403) or not login_success(home):
                raise PermissionError("PowerSchool login failed")
            students = find_students(home["body"])
        return students

    def discover_students(self):
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        students = self._login_and_discover()
        selected = {str(x) for x in (selected_ids or [])}
        if selected:
            students = [s for s in students if str(s["student_id"]) in selected]
        result = {}
        for st in students:
            student = process_student(st, photo_dir=self.photo_dir)
            courses = student.get("courses", []) or []
            assignments = [
                a for c in courses for a in (c.get("assignments", []) or [])
            ]
            graded = sum(
                1
                for a in assignments
                if a.get("percent") is not None or a.get("letter")
            )
            numeric_grades = [
                c.get("grade_percent")
                for c in courses
                if c.get("grade_percent") is not None
            ]
            student["course_count"] = len(courses)
            student["courses_with_assignments"] = sum(
                1 for c in courses if c.get("assignment_count", 0)
            )
            student["courses_without_assignments"] = sum(
                1 for c in courses if not c.get("assignment_count", 0)
            )
            student["assignment_count"] = len(assignments)
            student["graded_assignments"] = graded
            student["ungraded_assignments"] = len(assignments) - graded
            student["missing"] = sum(1 for a in assignments if a.get("missing"))
            student["late"] = sum(1 for a in assignments if a.get("late"))
            student["incomplete"] = sum(1 for a in assignments if a.get("incomplete"))
            student["exempt"] = sum(1 for a in assignments if a.get("exempt"))
            student["absent"] = sum(1 for a in assignments if a.get("absent"))
            student["collected"] = sum(1 for a in assignments if a.get("collected"))
            student["grade_average"] = (
                (sum(numeric_grades) / len(numeric_grades)) if numeric_grades else None
            )
            student["assignment_api_status"] = (
                "ok"
                if any(c.get("assignment_status") == "ok" for c in courses)
                else ("no_data" if courses else "no_courses")
            )
            student["identity_resolved"] = bool(student.get("student_dcid"))
            result[st["name"]] = student
        return {"students": result}


__all__ = ["PowerSchoolClient"]
