# Home Assistant adapter. The scraper functions are the tested v4 logic;
# this wrapper supplies instance-style configuration for the HA integration.
from __future__ import annotations

from http.cookiejar import CookieJar

from . import scraper as _s


class PowerSchoolClient:
    """Home Assistant adapter around the tested v4 PowerSchool protocol."""

    def __init__(self, base_url=None, username="", password="", term_start=None, term_end=None, photo_dir=None):
        self.base_url = (base_url or _s.BASE_URL).rstrip("/")
        self.username = username
        self.password = password
        self.term_start = term_start or _s.current_school_year_range()[0]
        self.term_end = term_end or _s.current_school_year_range()[1]
        self.photo_dir = photo_dir
        _s.BASE_URL = self.base_url
        _s.PUBLIC_URL = _s.BASE_URL + "/public/"
        _s.LOGIN_URL = _s.BASE_URL + "/guardian/home.html"
        _s.HOME_URL = _s.LOGIN_URL
        _s.LOOKUP_URL = ""
        if hasattr(_s, "ACTIVE_TERM_START"):
            _s.ACTIVE_TERM_START = self.term_start
        if hasattr(_s, "ACTIVE_TERM_END"):
            _s.ACTIVE_TERM_END = self.term_end
        _s.TIMEOUT = 30
        _s.DELAY = 0.25
        _s.GET_ASSIGNMENTS = True
        # Do not construct urllib SSL opener here (blocking on event loop).
        _s.jar = CookieJar()
        _s.opener = None

    def _login_and_discover(self):
        r = _s.login(self.username, self.password)
        if r["status"] in (401, 403) or not _s.login_success(r):
            raise PermissionError("PowerSchool login failed")
        students = _s.find_students(r["body"])
        if not students:
            home = _s.get(_s.HOME_URL)
            if home["status"] in (401, 403) or not _s.login_success(home):
                raise PermissionError("PowerSchool login failed")
            students = _s.find_students(home["body"])
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
            student = _s.process_student(st, photo_dir=self.photo_dir)
            courses = student.get("courses", []) or []
            assignments = [a for c in courses for a in (c.get("assignments", []) or [])]
            graded = sum(1 for a in assignments if a.get("percent") is not None or a.get("letter"))
            numeric_grades = [c.get("grade_percent") for c in courses if c.get("grade_percent") is not None]
            student["course_count"] = len(courses)
            student["courses_with_assignments"] = sum(1 for c in courses if c.get("assignment_count", 0))
            student["courses_without_assignments"] = sum(1 for c in courses if not c.get("assignment_count", 0))
            student["assignment_count"] = len(assignments)
            student["graded_assignments"] = graded
            student["ungraded_assignments"] = len(assignments) - graded
            student["missing"] = sum(1 for a in assignments if a.get("missing"))
            student["late"] = sum(1 for a in assignments if a.get("late"))
            student["incomplete"] = sum(1 for a in assignments if a.get("incomplete"))
            student["exempt"] = sum(1 for a in assignments if a.get("exempt"))
            student["absent"] = sum(1 for a in assignments if a.get("absent"))
            student["collected"] = sum(1 for a in assignments if a.get("collected"))
            student["grade_average"] = (sum(numeric_grades) / len(numeric_grades)) if numeric_grades else None
            student["assignment_api_status"] = (
                "ok" if any(c.get("assignment_status") == "ok" for c in courses) else (
                    "no_data" if courses else "no_courses"
                )
            )
            student["identity_resolved"] = bool(student.get("student_dcid"))
            result[st["name"]] = student
        return {"students": result}
