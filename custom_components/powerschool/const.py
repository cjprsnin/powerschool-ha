DOMAIN = "powerschool"
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_STUDENTS = "students"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_URL = ""
DEFAULT_UPDATE_INTERVAL = 15
PLATFORMS = ["sensor", "select", "binary_sensor"]

SERVICE_REFRESH = "refresh"

# Summary sensor fields: field -> (label, unit, diagnostic)
SUMMARY_FIELDS = {
    "grade_average": ("Grade Average", "%", False),
    "course_count": ("Course Count", None, False),
    "assignment_count": ("Assignment Count", None, False),
    "graded_assignments": ("Graded Assignments", None, False),
    "ungraded_assignments": ("Ungraded Assignments", None, False),
    "missing": ("Missing Assignments", None, False),
    "late": ("Late Assignments", None, False),
    "incomplete": ("Incomplete Assignments", None, True),
    "exempt": ("Exempt Assignments", None, True),
    "absent": ("Absent Assignments", None, True),
    "collected": ("Collected Assignments", None, True),
}
