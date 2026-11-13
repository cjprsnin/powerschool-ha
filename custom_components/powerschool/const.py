DOMAIN = "powerschool"
CONF_URL = "url"
CONF_NAME = "name"  # optional district / school label
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_STUDENTS = "students"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_DISTRICTS = "districts"  # list of {name,url,username,password,students}
DEFAULT_URL = ""
DEFAULT_UPDATE_INTERVAL = 30
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
    "absences": ("Absences", None, False),
    "tardies": ("Tardies", None, False),
    "upcoming_count": ("Upcoming Assignments", None, False),
    "due_soon_count": ("Due Soon Assignments", None, False),
    "schedule_count": ("Schedule Periods", None, True),
    "absent_days": ("Absent Days", None, False),
    "tardy_days": ("Tardy Days", None, False),
    "bulletin_count": ("Bulletin Items", None, True),
    "standards_course_count": ("Standards Courses", None, True),
    "class_roster_count": ("Class Roster", None, True),
    "grade_history_count": ("Grade History", None, True),
    "incomplete": ("Incomplete Assignments", None, True),
    "exempt": ("Exempt Assignments", None, True),
    "absent": ("Absent Assignments", None, True),
    "collected": ("Collected Assignments", None, True),
}

# Upcoming / due-soon windows (days)
DUE_SOON_DAYS = 2
UPCOMING_DAYS = 7

# Grade history
GRADE_HISTORY_MAX = 7
TREND_THRESHOLD = 0.5  # percentage points
