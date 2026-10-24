from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

SUMMARY_FIELDS = {
    "grade_average": ("Grade Average", PERCENTAGE),
    "course_count": ("Course Count", None),
    "assignment_count": ("Assignment Count", None),
    "graded_assignments": ("Graded Assignments", None),
    "ungraded_assignments": ("Ungraded Assignments", None),
    "missing": ("Missing Assignments", None),
    "late": ("Late Assignments", None),
    "incomplete": ("Incomplete Assignments", None),
    "exempt": ("Exempt Assignments", None),
    "absent": ("Absent Assignments", None),
    "collected": ("Collected Assignments", None),
}


def _slug(value):
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(value)).strip('_')


def _student_key(name, student):
    return f"{_slug(name)}_{student.get('student_id', '')}"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for name, student in coordinator.data.get('students', {}).items():
        key = _student_key(name, student)
        for field, (label, unit) in SUMMARY_FIELDS.items():
            entities.append(PowerSchoolSummarySensor(coordinator, name, student, key, field, label, unit))
        for course in student.get('courses', []):
            entities.append(PowerSchoolCourseSensor(coordinator, name, student, key, course))
    async_add_entities(entities)


class PowerSchoolSummarySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, student_name, student, key, field, label, unit):
        super().__init__(coordinator)
        self._student_name = student_name
        self._student_id = str(student.get('student_id', ''))
        self._field = field
        self._label = label
        self._attr_name = f"PowerSchool {student_name} {label}"
        self._attr_unique_id = f"powerschool_{key}_{field}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:school"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"student_{self._student_id}")},
            "name": f"PowerSchool {self._student_name}",
            "manufacturer": "PowerSchool",
            "model": "Student",
        }

    @property
    def native_value(self):
        student = self.coordinator.data.get('students', {}).get(self._student_name, {})
        return student.get(self._field, 0)

    @property
    def entity_picture(self):
        student = self.coordinator.data.get('students', {}).get(self._student_name, {})
        return student.get('photo_url')

    @property
    def extra_state_attributes(self):
        student = self.coordinator.data.get('students', {}).get(self._student_name, {})
        return {
            "student_id": student.get("student_id"),
            "student_dcid": student.get("student_dcid"),
            "student_frn": student.get("student_frn"),
            "identity_source": student.get("identity_source"),
            "identity_resolved": student.get("identity_resolved"),
            "assignment_api_status": student.get("assignment_api_status"),
            "photo_url": student.get("photo_url"),
            "photo_source_url": student.get("photo_source_url"),
            "courses_with_assignments": student.get("courses_with_assignments", 0),
            "courses_without_assignments": student.get("courses_without_assignments", 0),
            "last_update": self.coordinator.last_update_success,
        }


class PowerSchoolCourseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, student_name, student, key, course):
        super().__init__(coordinator)
        self._student_name = student_name
        self._course_name = course.get('course', 'Course')
        self._student_key = key
        self._student_id = str(student.get('student_id', ''))
        self._attr_name = f"PowerSchool {student_name} {self._course_name}"
        self._attr_unique_id = f"powerschool_{key}_course_{_slug(self._course_name)}"
        self._attr_icon = "mdi:book-education"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"student_{self._student_id}")},
            "name": f"PowerSchool {self._student_name}",
            "manufacturer": "PowerSchool",
            "model": "Student",
        }

    def _course(self):
        student = self.coordinator.data.get('students', {}).get(self._student_name, {})
        for course in student.get('courses', []):
            if course.get('course') == self._course_name:
                return course
        return {}

    @property
    def native_value(self):
        course = self._course()
        if course.get('grade_percent') is not None:
            return course.get('grade_percent')
        return course.get('grade_letter') or course.get('grade_raw') or None

    @property
    def native_unit_of_measurement(self):
        course = self._course()
        return PERCENTAGE if course.get('grade_percent') is not None else None

    @property
    def extra_state_attributes(self):
        course = self._course()
        assignments = []
        for a in course.get('assignments', []) or []:
            assignments.append({
                'name': a.get('name'), 'due': a.get('due'), 'category': a.get('category'),
                'earned': a.get('earned'), 'possible': a.get('possible'), 'percent': a.get('percent'),
                'letter': a.get('letter'), 'missing': a.get('missing', False), 'late': a.get('late', False),
                'incomplete': a.get('incomplete', False), 'exempt': a.get('exempt', False),
                'absent': a.get('absent', False), 'collected': a.get('collected', False),
                'counted_in_final_grade': a.get('counted_in_final_grade'),
                'assignment_id': a.get('assignment_id'), 'assignment_section_id': a.get('assignment_section_id')
            })
        graded = [
            a for a in assignments
            if a.get('percent') is not None or a.get('letter')
        ]
        missing = [a for a in assignments if a.get('missing')]

        def date_key(a):
            # Prefer the date the score was entered; fall back to modification/due.
            return (
                str(a.get('score_entry_date') or ''),
                str(a.get('when_modified') or ''),
                str(a.get('due') or ''),
            )

        graded.sort(key=date_key, reverse=True)
        latest = graded[0] if graded else None

        return {
            'student': self._student_name,
            'student_id': self._student_id_from_data(),
            'section_id': course.get('section_id'),
            'student_dcid': self.coordinator.data.get('students', {}).get(self._student_name, {}).get('student_dcid'),
            'student_frn': self.coordinator.data.get('students', {}).get(self._student_name, {}).get('student_frn'),
            'assignment_status': course.get('assignment_status'),
            'assignment_error': course.get('assignment_error'),
            'assignment_count': len(assignments),
            'graded_assignments': len(graded),
            'missing': len(missing),
            'late': sum(1 for a in assignments if a.get('late')),
            'last_graded_assignment': latest.get('name') if latest else None,
            'last_graded_percent': latest.get('percent') if latest else None,
            'last_graded_letter': latest.get('letter') if latest else None,
            'last_graded_earned': latest.get('earned') if latest else None,
            'last_graded_possible': latest.get('possible') if latest else None,
            'last_graded_date': latest.get('score_entry_date') if latest else None,
            'missing_homework': [
                {
                    'name': a.get('name'),
                    'due': a.get('due'),
                    'category': a.get('category'),
                    'late': a.get('late', False),
                    'assignment_id': a.get('assignment_id'),
                }
                for a in missing
            ],
            'assignments': assignments,
        }

    def _student_id_from_data(self):
        student = self.coordinator.data.get('students', {}).get(self._student_name, {})
        return student.get('student_id')
