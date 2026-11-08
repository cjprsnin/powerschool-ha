# Hearth ↔ PowerSchool HA

How the **Hearth** family wall panel can consume PowerSchool data from Home Assistant.

## Entity map (per student)

Replace `STUDENT` with the slug used in HA (e.g. `trent`, `teagan`).  
Some installs prefix with an area (`trent_s_bedroom_powerschool_trent_…`).

| Purpose | Entity pattern | State | Key attributes |
|--------|----------------|-------|----------------|
| Average | `sensor.powerschool_STUDENT_grade_average` | `%` or `unknown` | `student`, `photo_url` |
| Missing | `sensor.powerschool_STUDENT_missing_assignments` | count | |
| Late | `sensor.powerschool_STUDENT_late_assignments` | count | |
| Due soon | `sensor.…_due_soon_assignments` | count | `assignments[]` |
| Upcoming | `sensor.…_upcoming_assignments` | count | `assignments[]` |
| Absent days | `sensor.…_absent_days` | count | `attendance_days[]`, codes |
| **Class roster** | `sensor.…_class_roster` | count | **`class_roster[]`** |
| **Grade history** | `sensor.…_grade_history` | count | **`grade_history[]`** |
| Status | `sensor.…_status` | `ok` / error | diagnostics |
| Per course | `sensor.…_COURSE` | `%` or letter | `teacher`, `room`, `section_id`, `assignments[]`, `term_grades` |

### `class_roster[]` item
```json
{
  "course": "Science 7",
  "section_id": "51672",
  "teacher": "Genco, Rebecca",
  "room": "154"
}
```
Lunch / recess / Staff rows are filtered out.

### `grade_history[]` item (stored / prior terms)
```json
{
  "course": "Science 6",
  "course_number": "SCI06",
  "letter": "A",
  "date_completed": "06/2025",
  "grade_level": "6",
  "school": "Elementary",
  "credit_earned": "1.0",
  "credit_attempted": "1.0",
  "is_current_term": false,
  "term_label": "06/2025"
}
```
Source: guardian `termgrades.html`. Empty until the district exposes history.

### `assignments[]` (due soon / upcoming / course)
```json
{
  "name": "Chapter 4 quiz",
  "course": "Science 7",
  "due": "2026-11-10",
  "days_until_due": 2,
  "missing": false,
  "late": false,
  "percent": null
}
```

## Suggested Hearth widgets

1. **At a glance** — average, missing, due-soon count, absent days  
2. **Classes** — list from `class_roster` (course · teacher · room)  
3. **Due soon** — `due_soon_assignments.attributes.assignments`  
4. **History** — `grade_history` when status is `ok`  

## Fetching from HA

Use the HA REST API or WebSocket from Hearth (same long-lived token you use for other panels):

```http
GET /api/states/sensor.trent_s_bedroom_powerschool_trent_class_roster
Authorization: Bearer <TOKEN>
```

Response `attributes.class_roster` is the list above.

## Brand notes (Hearth palette)
- Background `#0c0c0e`
- Foreground `#ecece8`
- Accent steel `#c8ccd4`
- Lights / warm `#c4a574`

Keep school tiles calm and kiosk-like; prefer roster + due-soon over dense grade tables on the wall panel.
