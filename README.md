# PowerSchool Grades for Home Assistant

Unofficial Home Assistant integration for the PowerSchool Parent Portal.

Pulls grades, assignment counts, missing/late work, and course details for selected students. Updates on a configurable interval (default 15 minutes).

## Installation

### HACS (recommended)

1. In HACS → Integrations → ⋮ → **Custom repositories**
2. Add repository URL: `https://github.com/cjprsnin/powerschool-ha`
3. Category: **Integration**
4. Click **Add**
5. Search for **PowerSchool Grades** and install
6. Restart Home Assistant
7. Settings → Devices & services → **Add integration** → **PowerSchool Grades**
8. Enter your PowerSchool URL (e.g. `https://powerschool.yourdistrict.org`), username, and password
9. Select which students to monitor

### Manual

1. Copy `custom_components/powerschool` into your HA config folder (`/config/custom_components/`)
2. Restart Home Assistant
3. Add the integration as above

## Entities

Per selected student:

| Entity pattern | Description |
|----------------|-------------|
| `sensor.powerschool_<student>_grade_average` | Average of course grade percentages |
| `sensor.powerschool_<student>_course_count` | Number of courses |
| `sensor.powerschool_<student>_assignment_count` | Total assignments |
| `sensor.powerschool_<student>_missing_assignments` | Missing count |
| `sensor.powerschool_<student>_late_assignments` | Late count |
| `sensor.powerschool_<student>_<course>` | Course grade (percent or letter) |

Course sensors include assignment lists and missing-homework details in attributes.

Also creates `select.powerschool_student` to pick the active student for dashboards that need one.

Student photos (when available from the portal) are stored under `/local/powerschool/` and used as entity pictures.

## Options

After setup: integration → **Configure** to change URL, credentials, selected students, or update interval (5–1440 minutes).

## Notes

- Uses the PowerSchool guardian/parent portal (not the public API)
- Polls on the interval you set; keep it reasonable to avoid stressing the district server
- Version: 1.2.0
