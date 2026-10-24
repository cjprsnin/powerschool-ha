# PowerSchool Grades for Home Assistant

Unofficial Home Assistant integration for the PowerSchool Parent Portal.

Pulls grades, assignment counts, missing/late work, course details, and **student profile photos** for selected students.

**Version:** 1.3.0

## Features

- Config flow setup (URL, credentials, student selection)
- Per-student summary sensors (average, missing, late, …)
- Per-course grade sensors with full assignment attributes
- Binary sensors: has missing work / has late work
- Student profile photos as `entity_picture` (from the portal)
- Diagnostic status sensor (identity + assignment API health)
- Service: `powerschool.refresh`
- Example Lovelace cards + notification blueprint

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. Add `https://github.com/cjprsnin/powerschool-ha` as **Integration**
3. Install **PowerSchool Grades** → restart Home Assistant
4. Settings → Devices & services → **Add integration** → **PowerSchool Grades**
5. Enter PowerSchool URL (e.g. `https://powerschool.yourdistrict.org`), username, password
6. Select students to monitor

### Manual

Copy `custom_components/powerschool` into `/config/custom_components/`, restart, then add the integration.

## Profile pictures

When the parent portal exposes a student photo, the integration:

1. Downloads it into `/config/www/powerschool/`
2. Serves it as `/local/powerschool/<student_id>.jpg` (or `.png`/`.webp`)
3. Sets it as `entity_picture` on summary sensors, binary sensors, and the student select

**In Lovelace**, photos show automatically on entities cards and glance cards. For mushroom/template cards use:

```yaml
picture: "{{ state_attr('sensor.powerschool_STUDENT_NAME_grade_average', 'photo_url') }}"
```

If no photo appears, the district portal likely does not expose one on the guardian home page (or blocks the image request). Check `photo_url` / `photo_source_url` on the grade average sensor attributes.

## Entities (per student)

| Pattern | Description |
|---------|-------------|
| `sensor.powerschool_<student>_grade_average` | Average of course % grades |
| `sensor.powerschool_<student>_missing_assignments` | Missing count |
| `sensor.powerschool_<student>_late_assignments` | Late count |
| `sensor.powerschool_<student>_status` | Diagnostic: identity / API status |
| `sensor.powerschool_<student>_<course>` | Course grade |
| `binary_sensor.powerschool_<student>_has_missing_work` | Problem sensor |
| `binary_sensor.powerschool_<student>_has_late_work` | Problem sensor |
| `select.powerschool_student` | Active student picker |

Course unique IDs prefer PowerSchool `section_id` so renames do not orphan entities.

## Services

```yaml
service: powerschool.refresh
```

Forces an immediate poll of all configured PowerSchool entries.

## Options

Integration → **Configure**: URL, credentials, students, update interval (5–1440 minutes).

## Lovelace examples

See [`examples/lovelace-cards.yaml`](examples/lovelace-cards.yaml) and [`examples/dashboard-view.yaml`](examples/dashboard-view.yaml).

## Notifications

Import the blueprint from [`blueprints/automation/powerschool_missing_work.yaml`](blueprints/automation/powerschool_missing_work.yaml) (or copy into `/config/blueprints/automation/`).

## Notes

- Uses the guardian/parent portal (not a public API)
- Poll reasonably; default is 15 minutes
- Photos are cached under `www/powerschool/` and refreshed on each successful poll when the portal provides a new image
