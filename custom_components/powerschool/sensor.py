from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SUMMARY_FIELDS


def _slug(value):
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _student_key(name, student):
    return f"{_slug(name)}_{student.get('student_id', '')}"


def _course_uid(key, course):
    """Stable course unique id: prefer section_id, fall back to slugified name."""
    section = course.get("section_id")
    if section:
        return f"powerschool_{key}_section_{section}"
    return f"powerschool_{key}_course_{_slug(course.get('course', 'course'))}"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for name, student in coordinator.data.get("students", {}).items():
        key = _student_key(name, student)
        for field, (label, unit, diagnostic) in SUMMARY_FIELDS.items():
            entities.append(
                PowerSchoolSummarySensor(
                    coordinator, name, student, key, field, label, unit, diagnostic
                )
            )
        entities.append(PowerSchoolDiagnosticSensor(coordinator, name, student, key))
        for course in student.get("courses", []):
            entities.append(PowerSchoolCourseSensor(coordinator, name, student, key, course))
    async_add_entities(entities)


class _StudentEntity(CoordinatorEntity):
    def __init__(self, coordinator, student_name, student, key):
        super().__init__(coordinator)
        self._student_name = student_name
        self._student_id = str(student.get("student_id", ""))
        self._student_key = key

    def _student(self):
        return self.coordinator.data.get("students", {}).get(self._student_name, {})

    @property
    def device_info(self):
        student = self._student()
        info = {
            "identifiers": {(DOMAIN, f"student_{self._student_id}")},
            "name": f"PowerSchool {self._student_name}",
            "manufacturer": "PowerSchool",
            "model": "Student",
        }
        return info

    @property
    def entity_picture(self):
        return self._student().get("photo_url")


class PowerSchoolSummarySensor(_StudentEntity, SensorEntity):
    def __init__(self, coordinator, student_name, student, key, field, label, unit, diagnostic):
        super().__init__(coordinator, student_name, student, key)
        self._field = field
        self._attr_name = f"PowerSchool {student_name} {label}"
        self._attr_unique_id = f"powerschool_{key}_{field}"
        self._attr_native_unit_of_measurement = unit
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self._student().get(self._field)

    @property
    def extra_state_attributes(self):
        student = self._student()
        return {
            "student": self._student_name,
            "student_id": self._student_id,
            "student_dcid": student.get("student_dcid"),
            "student_frn": student.get("student_frn"),
            "photo_url": student.get("photo_url"),
            "photo_source_url": student.get("photo_source_url"),
            "last_update_success": self.coordinator.last_update_success,
        }


class PowerSchoolDiagnosticSensor(_StudentEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator, student_name, student, key):
        super().__init__(coordinator, student_name, student, key)
        self._attr_name = f"PowerSchool {student_name} Status"
        self._attr_unique_id = f"powerschool_{key}_status"

    @property
    def native_value(self):
        student = self._student()
        if not student:
            return "no_data"
        if student.get("error"):
            return "error"
        courses = student.get("courses") or []
        if not courses:
            return "no_data"
        return "ok"

    @property
    def extra_state_attributes(self):
        student = self._student()
        return {
            "student": self._student_name,
            "student_id": self._student_id,
            "student_dcid": student.get("student_dcid"),
            "student_frn": student.get("student_frn"),
            "identity_source": student.get("identity_source"),
            "course_count": student.get("course_count"),
            "assignment_count": student.get("assignment_count"),
            "last_update_success": self.coordinator.last_update_success,
        }


class PowerSchoolCourseSensor(_StudentEntity, SensorEntity):
    def __init__(self, coordinator, student_name, student, key, course):
        super().__init__(coordinator, student_name, student, key)
        self._course_name = course.get("course", "Course")
        self._section_id = course.get("section_id")
        self._attr_name = f"PowerSchool {student_name} {self._course_name}"
        self._attr_unique_id = _course_uid(key, course)
        self._attr_icon = "mdi:book-education"

    def _course(self):
        student = self._student()
        if self._section_id:
            for course in student.get("courses", []):
                if str(course.get("section_id") or "") == str(self._section_id):
                    return course
        for course in student.get("courses", []):
            if course.get("course") == self._course_name:
                return course
        return {}

    @property
    def native_value(self):
        course = self._course()
        if course.get("grade_percent") is not None:
            return course.get("grade_percent")
        return course.get("grade_letter") or course.get("grade_raw") or None

    @property
    def native_unit_of_measurement(self):
        course = self._course()
        return PERCENTAGE if course.get("grade_percent") is not None else None

    @property
    def extra_state_attributes(self):
        course = self._course()
        assignments = []
        for a in course.get("assignments", []) or []:
            assignments.append(
                {
                    "name": a.get("name"),
                    "due": a.get("due"),
                    "category": a.get("category"),
                    "earned": a.get("earned"),
                    "possible": a.get("possible"),
                    "percent": a.get("percent"),
                    "letter": a.get("letter"),
                    "missing": a.get("missing", False),
                    "late": a.get("late", False),
                    "incomplete": a.get("incomplete", False),
                    "exempt": a.get("exempt", False),
                    "absent": a.get("absent", False),
                    "collected": a.get("collected", False),
                    "counted_in_final_grade": a.get("counted_in_final_grade"),
                    "assignment_id": a.get("assignment_id"),
                    "assignment_section_id": a.get("assignment_section_id"),
                    "score_entry_date": a.get("score_entry_date"),
                }
            )
        graded = [a for a in assignments if a.get("percent") is not None or a.get("letter")]
        missing = [a for a in assignments if a.get("missing")]
        latest = None
        if graded:
            latest = sorted(
                graded,
                key=lambda a: (
                    str(a.get("score_entry_date") or ""),
                    str(a.get("due") or ""),
                ),
                reverse=True,
            )[0]

        return {
            "student": self._student_name,
            "student_id": self._student_id,
            "section_id": course.get("section_id"),
            "student_dcid": self._student().get("student_dcid"),
            "student_frn": self._student().get("student_frn"),
            "assignment_status": course.get("assignment_status"),
            "assignment_error": course.get("assignment_error"),
            "assignment_count": len(assignments),
            "graded_assignments": len(graded),
            "missing": len(missing),
            "late": sum(1 for a in assignments if a.get("late")),
            "last_graded_assignment": latest.get("name") if latest else None,
            "last_graded_percent": latest.get("percent") if latest else None,
            "last_graded_letter": latest.get("letter") if latest else None,
            "last_graded_earned": latest.get("earned") if latest else None,
            "last_graded_possible": latest.get("possible") if latest else None,
            "last_graded_date": latest.get("score_entry_date") if latest else None,
            "store_code": course.get("store_code"),
            "term_id": course.get("term_id"),
            "term_start": course.get("term_start"),
            "term_end": course.get("term_end"),
            "is_current_term": course.get("is_current_term", True),
            "term_label": course.get("term_label"),
            "missing_homework": [
                {
                    "name": a.get("name"),
                    "due": a.get("due"),
                    "category": a.get("category"),
                    "late": a.get("late", False),
                    "assignment_id": a.get("assignment_id"),
                }
                for a in missing
            ],
            "assignments": assignments,
        }
