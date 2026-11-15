#!/usr/bin/env python3
"""Fix schedule false positives from home grade table; skip 'Not available' term cells."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
code = path.read_text()
if 'def parse_schedule' not in code:
    sys.exit('parse_schedule missing')

i = code.find('def parse_schedule(src):')
j = code.find('\ndef parse_attendance_days', i)
if j < 0:
    j = code.find('\ndef parse_bulletin', i)
if i < 0 or j < 0:
    sys.exit('bounds not found for parse_schedule')

new_sched = r'''def parse_schedule(src):
    if not src:
        return []
    junk_course = re.compile(
        r'^(attendance\s*totals?|totals?|period|course|class|teacher|room|time|'
        r'day|schedule|homeroom\s*attendance|present|absent|tardy|'
        r'not\s*available|n/?a|\d{2}-\d{2}|exp|y1|t[1-4]|q[1-4])$',
        re.I,
    )
    year_re = re.compile(r'^\d{2}-\d{2}$')
    def is_period(c):
        c = (c or '').strip()
        if re.fullmatch(r'\d{1,2}', c):
            return c != '0'
        if re.fullmatch(r'P(?:er(?:iod)?)?\s*\d{1,2}', c, re.I):
            return True
        if re.fullmatch(r'\d{1,2}[A-Za-z]', c):
            return True
        return False

    rows = []
    tables = re.findall(r'<table\b[^>]*>(.*?)</table>', src, re.I|re.S)
    search_blobs = tables if tables else [src]
    for blob_html in search_blobs:
        for tm in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', blob_html, re.I|re.S):
            cells = [strip(x) for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tm.group(1), re.I|re.S)]
            cells = [c for c in cells if c]
            if len(cells) < 2:
                continue
            blob = ' '.join(cells).lower()
            if re.search(r'\bperiod\b', blob) and re.search(r'\b(course|class|teacher)\b', blob):
                continue
            if 'attendance totals' in blob:
                continue
            if re.search(r'\b(absences?|tardies?)\b', blob) and re.search(r'\b(email|rm:|room:)\b', blob):
                continue
            period = None
            for c in cells[:3]:
                if is_period(c):
                    period = c
                    break
            if not period:
                continue
            course = ''
            room = ''
            teacher = ''
            times = ''
            for c in cells:
                if c == period:
                    continue
                if year_re.match(c):
                    continue
                if re.search(r'\d{1,2}:\d{2}\s*[AaPp][Mm]', c):
                    times = c
                elif re.search(r'\broom\b', c, re.I) or (re.fullmatch(r'(?:Rm:?\s*)?[A-Z]?\d{2,4}[A-Z]?', c, re.I) and len(c) < 14):
                    if not room:
                        room = c
                elif not course and len(c) > 2:
                    course = c
                elif course and not teacher and len(c) > 2 and c not in (times, room, course):
                    if ' ' in c or ',' in c:
                        teacher = c
            if not course or junk_course.match(course.strip()) or year_re.match(course.strip()):
                continue
            if re.search(r'\bRoom:\s*', course) or re.search(r'\bEmail\b', course) or len(course) > 80:
                m = re.match(r'^([^(]+?)(?:\s+\d{3,5}|\s+\.|$)', course)
                if m and len(m.group(1).strip()) > 2:
                    course = m.group(1).strip()
                else:
                    continue
            if junk_course.match(course.strip()):
                continue
            if not (times or room or teacher or ' ' in course):
                continue
            rows.append({
                'period': period,
                'course': course,
                'teacher': teacher or None,
                'room': room or None,
                'time': times or None,
            })
        if rows:
            break
    seen = set()
    out = []
    for r in rows:
        key = (r['period'], r['course'])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

'''

code = code[:i] + new_sched + code[j:]
print('replaced parse_schedule')

old = '''def scrape_portal_extras(home_src=None):
    schedule, schedule_status = [], 'unavailable'
    if home_src:
        rows = parse_schedule(home_src)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from home.html rows=%s' % len(rows))
    if schedule_status != 'ok':
        for path in'''

new = '''def scrape_portal_extras(home_src=None):
    schedule, schedule_status = [], 'unavailable'
    for path in'''

if old in code:
    code = code.replace(old, new, 1)
    old2 = '''            if rows:
                schedule, schedule_status = rows, 'ok'
                debug('schedule from %s rows=%s' % (url, len(rows)))
                break
    attendance ='''
    new2 = '''            if rows:
                schedule, schedule_status = rows, 'ok'
                debug('schedule from %s rows=%s' % (url, len(rows)))
                break
    if schedule_status != 'ok' and home_src:
        rows = parse_schedule(home_src)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from home.html rows=%s' % len(rows))
    attendance ='''
    if old2 in code:
        code = code.replace(old2, new2, 1)
        print('schedule: dedicated pages first, home last')
    else:
        print('WARN: could not rewire home fallback')
else:
    print('scrape order already changed or mismatch')

old_tg = '''            raw=values[tidx]
            if not raw or raw in ('','-','--','—','N/A','n/a','.'):
                continue'''
new_tg = '''            raw=values[tidx]
            if not raw or raw in ('','-','--','—','N/A','n/a','.'):
                continue
            if re.search(r'not\\s*available', raw, re.I):
                continue'''
if old_tg in code:
    code = code.replace(old_tg, new_tg, 1)
    print('skip Not available term cells')
else:
    print('WARN: term skip needle missing')

needle = '    # Elementary / standards proficiency scales'
if needle in code and "re.search(r'not\\s*available', t, re.I)" not in code[code.find('def grade_value'):code.find('def grade_value')+1200]:
    code = code.replace(
        needle,
        "    if re.search(r'not\\s*available', t, re.I):\n        return {}\n" + needle,
        1,
    )
    print('grade_value rejects Not available')

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError', e)
    sys.exit(1)

path.write_text(code)
print('OK')
