#!/usr/bin/env python3
"""Scrape guardian termgrades.html (stored/historical grades) into grade_history."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
code = path.read_text()

if 'def parse_grade_history' in code:
    print('parse_grade_history already present')
else:
    i = code.find('def scrape_portal_extras')
    if i < 0:
        sys.exit('scrape_portal_extras not found')
    helper = r'''def parse_grade_history(src):
    """Parse guardian termgrades.html stored-grade table.

    Typical columns: Date Compl | Grade Level | School | Course # | Course |
    Credit Earned | Credit Attempted | Grade
    """
    if not src:
        return []
    rows = []
    tables = re.findall(r'<table\b[^>]*>(.*?)</table>', src, re.I|re.S)
    blobs = tables if tables else [src]
    for blob in blobs:
        for tm in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', blob, re.I|re.S):
            cells = [strip(x) for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tm.group(1), re.I|re.S)]
            cells = [c for c in cells if c]
            if len(cells) < 4:
                continue
            blob_l = ' '.join(cells).lower()
            if 'date' in blob_l and 'course' in blob_l and ('credit' in blob_l or 'grade' in blob_l):
                continue
            if 'course' in blob_l and 'credit earned' in blob_l:
                continue
            date_compl = None
            grade_level = None
            school = None
            course_num = None
            course = None
            credit_earned = None
            credit_attempted = None
            letter = None
            if len(cells) >= 8:
                date_compl = cells[0]
                grade_level = cells[1]
                school = cells[2]
                course_num = cells[3]
                course = cells[4]
                credit_earned = cells[5]
                credit_attempted = cells[6]
                letter = cells[7]
            else:
                for c in cells:
                    if re.fullmatch(r'\d{1,2}/\d{4}', c) or re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2,4}', c):
                        date_compl = date_compl or c
                    elif re.fullmatch(r'\d{1,2}', c) and grade_level is None and int(c) <= 12:
                        grade_level = c
                    elif re.fullmatch(r'[A-F][+-]?|\d{1,3}(?:\.\d+)?%?', c, re.I) and letter is None and c not in (grade_level or ''):
                        letter = c
                    elif re.fullmatch(r'\d+(?:\.\d+)?', c) and credit_earned is None:
                        credit_earned = c
                    elif not course and len(c) > 3 and not re.search(r'http', c, re.I):
                        if course_num is None and re.fullmatch(r'[A-Z0-9.-]{2,12}', c):
                            course_num = c
                        else:
                            course = c
            if not course or not letter:
                continue
            if re.search(r'^(course|grade|date|school|credit)', course, re.I):
                continue
            rows.append({
                'course': course,
                'course_number': course_num,
                'letter': letter,
                'date_completed': date_compl,
                'grade_level': grade_level,
                'school': school,
                'credit_earned': credit_earned,
                'credit_attempted': credit_attempted,
                'is_current_term': False,
                'term_label': date_compl or 'History',
            })
        if rows:
            break
    return rows


'''
    code = code[:i] + helper + code[i:]
    print('added parse_grade_history')

if 'grade_history_status' not in code:
    marker = "    return {\n        'schedule': schedule,"
    if marker not in code:
        sys.exit('return marker not found')
    inject = """    history, history_status = [], 'unavailable'
    for path in ('termgrades.html', 'historicalGrades.html', 'gradeHistory.html', 'gradeshistory.html'):
        body, url, status = fetch_html(path)
        if not body:
            continue
        rows = parse_grade_history(body)
        if rows:
            history, history_status = rows, 'ok'
            debug('grade history from %s rows=%s' % (url, len(rows)))
            break

    return {
        'schedule': schedule,"""
    code = code.replace(marker, inject, 1)
    code = code.replace(
        "'bulletin_count': len(bulletin),\n    }",
        "'bulletin_count': len(bulletin),\n"
        "        'grade_history': history,\n"
        "        'grade_history_status': history_status,\n"
        "        'grade_history_count': len(history),\n"
        "    }",
        1,
    )
    print('wired grade history into scrape_portal_extras')
else:
    print('grade_history already in extras')

if "setdefault('grade_history_status'" not in code:
    code = code.replace(
        "result.setdefault('bulletin_status', 'unavailable')",
        "result.setdefault('bulletin_status', 'unavailable')\n"
        "        result.setdefault('grade_history_status', 'unavailable')",
        1,
    )
    print('added history default')

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError', e)
    sys.exit(1)

path.write_text(code)
print('OK client')

const = Path('custom_components/powerschool/const.py')
c = const.read_text()
if 'grade_history_count' not in c:
    c = c.replace(
        '    "class_roster_count": ("Class Roster", None, True),',
        '    "class_roster_count": ("Class Roster", None, True),\n'
        '    "grade_history_count": ("Grade History", None, True),',
        1,
    )
    const.write_text(c)
    print('const grade_history_count')

sensor = Path('custom_components/powerschool/sensor.py')
s = sensor.read_text()
if 'grade_history_status' not in s:
    if 'elif self._field == "class_roster_count":' in s:
        s = s.replace(
            'elif self._field == "class_roster_count":\n            attrs["class_roster"] = student.get("class_roster") or []\n',
            'elif self._field == "class_roster_count":\n            attrs["class_roster"] = student.get("class_roster") or []\n'
            '        elif self._field == "grade_history_count":\n'
            '            attrs["grade_history_status"] = student.get("grade_history_status")\n'
            '            attrs["grade_history"] = student.get("grade_history") or []\n',
            1,
        )
        print('sensor grade_history attrs')
    elif 'elif self._field == "bulletin_count":' in s:
        s = s.replace(
            'elif self._field == "bulletin_count":\n            attrs["bulletin_status"] = student.get("bulletin_status")\n            attrs["bulletin"] = student.get("bulletin") or []\n',
            'elif self._field == "bulletin_count":\n            attrs["bulletin_status"] = student.get("bulletin_status")\n            attrs["bulletin"] = student.get("bulletin") or []\n'
            '        elif self._field == "grade_history_count":\n'
            '            attrs["grade_history_status"] = student.get("grade_history_status")\n'
            '            attrs["grade_history"] = student.get("grade_history") or []\n',
            1,
        )
        print('sensor grade_history attrs via bulletin')
    sensor.write_text(s)

print('OK')
