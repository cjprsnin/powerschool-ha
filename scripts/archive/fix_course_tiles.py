#!/usr/bin/env python3
"""Restore V2/V3 cards from last good commit and exclude summary sensors."""
import urllib.request
from pathlib import Path

REF = "d1c49c799cbe80cb1cb36334cddfd5e643a89fc5"
OLD = "_isCourseSensor(s){const a=s.attributes||{};return s.entity_id.startsWith('sensor.')&&('section_id' in a||'assignments' in a||'course' in a)&&('student' in a);}"
NEW = "_isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming_assignments|grade_average|missing_assignments|late_assignments|_status$|absences|tardies/.test(eid))return false;return 'section_id' in a||'missing_homework' in a||'assignment_status' in a;}"

root = Path("www")
root.mkdir(exist_ok=True)
for name in ("powerschool-v2-card.js", "powerschool-v3-card.js"):
    url = f"https://raw.githubusercontent.com/cjprsnin/powerschool-ha/{REF}/www/{name}"
    text = urllib.request.urlopen(url).read().decode()
    if OLD not in text:
        raise SystemExit(f"{name}: expected _isCourseSensor not found")
    text = text.replace(OLD, NEW, 1)
    (root / name).write_text(text)
    print("Wrote", root / name, len(text))
print("Done — commit and push, then hard-refresh the dashboard.")
