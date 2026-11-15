#!/usr/bin/env python3
"""Filter lunch/recess/staff from class_roster for cleaner Hearth consumption."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
code = path.read_text()

if "if 'lunch' in cl or 'recess' in cl:" in code:
    print('roster filter already present')
    sys.exit(0)

old = """        roster=[]
        for cr in result.get('courses') or []:
            if not cr.get('course'):
                continue
            roster.append({
                'course': cr.get('course'),
                'section_id': cr.get('section_id'),
                'teacher': cr.get('teacher'),
                'room': cr.get('room'),
            })
        result['class_roster']=roster
        result['class_roster_count']=len(roster)"""

new = """        roster=[]
        for cr in result.get('courses') or []:
            course=cr.get('course') or ''
            if not course:
                continue
            cl=course.lower()
            tl=(cr.get('teacher') or '').lower()
            # Skip non-instructional rows for Hearth / wall-panel use
            if 'lunch' in cl or 'recess' in cl:
                continue
            if tl in ('staff, staff', 'staff staff', 'staff'):
                continue
            roster.append({
                'course': course,
                'section_id': cr.get('section_id'),
                'teacher': cr.get('teacher'),
                'room': cr.get('room'),
            })
        result['class_roster']=roster
        result['class_roster_count']=len(roster)"""

if old not in code:
    sys.exit('roster block not found')
code = code.replace(old, new, 1)
compile(code, 'client_body.py', 'exec')
path.write_text(code)
print('applied roster filter')
print('OK')
