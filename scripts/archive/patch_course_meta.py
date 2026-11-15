#!/usr/bin/env python3
"""Extract teacher + room from home grade table course cells; expose as class_roster."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
code = path.read_text()

if 'def parse_course_meta' not in code:
    j = code.find('\ndef num(')
    if j < 0:
        sys.exit('def num not found')
    helper = '''
def parse_course_meta(text):
    """Pull teacher + room from the raw Course cell text."""
    text=norm(text)
    teacher=None
    room=None
    if not text:
        return teacher, room
    m=re.search(r'\\bEmail\\s+(.+?)(?:\\s+-\\s+Rm:|\\s+Rm:|$)', text, re.I)
    if m:
        teacher=norm(m.group(1)) or None
    m=re.search(r'\\bRm:\\s*([^\\s,;]+)', text, re.I)
    if m:
        room=norm(m.group(1)) or None
    if not room:
        m=re.search(r'\\bRoom:\\s*([^\\s,;]+)', text, re.I)
        if m:
            room=norm(m.group(1)) or None
    return teacher, room

'''
    code = code[:j] + helper + code[j:]
    print('added parse_course_meta')
else:
    print('parse_course_meta already present')

if 'parse_course_meta(course_raw)' not in code:
    marker = "debug('Skipping ccid row %s: could not identify Course cell' % row_id)"
    idx = code.find(marker)
    if idx < 0:
        sys.exit('course skip marker not found')
    idx2 = code.find('continue', idx)
    idx2 = code.find('\n', idx2) + 1
    insert = (
        "\n"
        "        course_raw = ''\n"
        "        if course_index is not None and course_index < len(row.get('cells', [])):\n"
        "            course_raw = norm(row['cells'][course_index].get('text', ''))\n"
        "        teacher, room = parse_course_meta(course_raw)\n"
    )
    code = code[:idx2] + insert + code[idx2:]
    print('inserted meta extract')
else:
    print('meta extract already present')

if "'teacher':teacher" not in code:
    target = "'absences':absences,\n            'tardies':tardies,\n        })"
    if target not in code:
        sys.exit('output.append tail not found')
    code = code.replace(
        target,
        "'absences':absences,\n            'tardies':tardies,\n            'teacher':teacher,\n            'room':room,\n        })",
        1,
    )
    print('output includes teacher/room')
else:
    print('teacher already in output')

bulk_old = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','grade_level','grade_scale','term_grades','section_id','absences','tardies')}"
bulk_new = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','grade_level','grade_scale','term_grades','section_id','absences','tardies','teacher','room')}"
if bulk_old in code:
    code = code.replace(bulk_old, bulk_new, 1)
    print('bulk keys include teacher/room')
elif "'teacher','room')" in code:
    print('bulk already has teacher')
else:
    print('WARN: bulk keys not updated')

if "result['class_roster']" not in code:
    needle = "        extras = scrape_portal_extras(home_src=src)"
    if needle not in code:
        sys.exit('extras needle not found')
    inject = (
        "        roster=[]\n"
        "        for cr in result.get('courses') or []:\n"
        "            if not cr.get('course'):\n"
        "                continue\n"
        "            roster.append({\n"
        "                'course': cr.get('course'),\n"
        "                'section_id': cr.get('section_id'),\n"
        "                'teacher': cr.get('teacher'),\n"
        "                'room': cr.get('room'),\n"
        "            })\n"
        "        result['class_roster']=roster\n"
        "        result['class_roster_count']=len(roster)\n"
        + needle
    )
    code = code.replace(needle, inject, 1)
    print('added class_roster on result')
else:
    print('class_roster already present')

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError', e)
    sys.exit(1)

path.write_text(code)
print('OK client')

sensor = Path('custom_components/powerschool/sensor.py')
s = sensor.read_text()
if 'course.get("teacher")' not in s:
    for marker in [
        '            "term_grades": course.get("term_grades") or {},\n        }',
        '            "tardies": course.get("tardies"),\n        }',
    ]:
        if marker in s:
            s = s.replace(
                marker,
                marker.replace(
                    '\n        }',
                    '\n            "teacher": course.get("teacher"),\n'
                    '            "room": course.get("room"),\n'
                    '        }',
                ),
                1,
            )
            print('sensor course attrs teacher/room')
            break
    else:
        print('WARN: sensor course attrs marker missing')

if 'elif self._field == "bulletin_count":' in s and 'class_roster_count' not in s:
    s = s.replace(
        'elif self._field == "bulletin_count":\n            attrs["bulletin_status"] = student.get("bulletin_status")\n            attrs["bulletin"] = student.get("bulletin") or []\n',
        'elif self._field == "bulletin_count":\n            attrs["bulletin_status"] = student.get("bulletin_status")\n            attrs["bulletin"] = student.get("bulletin") or []\n'
        '        elif self._field == "class_roster_count":\n            attrs["class_roster"] = student.get("class_roster") or []\n',
        1,
    )
    print('sensor summary class_roster attrs')

sensor.write_text(s)

const = Path('custom_components/powerschool/const.py')
c = const.read_text()
if 'class_roster_count' not in c:
    for needle in [
        '    "standards_course_count": ("Standards Courses", None, True),',
        '    "bulletin_count": ("Bulletin Items", None, True),',
        '    "schedule_count": ("Schedule Periods", None, True),',
    ]:
        if needle in c:
            const.write_text(c.replace(
                needle,
                needle + '\n    "class_roster_count": ("Class Roster", None, True),',
                1,
            ))
            print('const class_roster_count')
            break

print('OK')
