#!/usr/bin/env python3
"""Tighten schedule + bulletin parsers (reject junk rows, better PS patterns)."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
if not path.exists():
    sys.exit('Run from repo root')

code = path.read_text()
if 'def parse_schedule' not in code:
    sys.exit('parse_schedule missing — apply portal extras first')

old_sched = '''def parse_schedule(src):
    if not src:
        return []
    rows = []
    for tm in re.finditer(r'<tr\\b[^>]*>(.*?)</tr>', src, re.I|re.S):
        cells = [strip(x) for x in re.findall(r'<t[dh]\\b[^>]*>(.*?)</t[dh]>', tm.group(1), re.I|re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        blob = ' '.join(cells).lower()
        if 'period' in blob and ('course' in blob or 'class' in blob) and len(cells) >= 3:
            continue
        period = None
        for c in cells[:3]:
            if re.fullmatch(r'\\d{1,2}[A-Za-z]?', c) or re.fullmatch(r'[A-H]', c) or re.match(r'^P(?:er(?:iod)?)?\\s*\\d+', c, re.I):
                period = c
                break
        if not period:
            continue
        course = ''
        room = ''
        teacher = ''
        times = ''
        for c in cells:
            if re.search(r'\\d{1,2}:\\d{2}\\s*[AaPp][Mm]', c):
                times = c
            elif re.search(r'\\broom\\b', c, re.I) or (re.fullmatch(r'[A-Z]?\\d{2,4}[A-Z]?', c) and len(c) < 12):
                if not room:
                    room = c
            elif not course and len(c) > 3 and c != period:
                course = c
            elif course and not teacher and len(c) > 3 and c not in (period, times, room, course):
                teacher = c
        if course:
            rows.append({'period': period, 'course': course, 'teacher': teacher or None, 'room': room or None, 'time': times or None})
    return rows'''

# Use bounds replace for reliability
i = code.find('def parse_schedule(src):')
j = code.find('\ndef parse_attendance_days', i)
if j < 0:
    j = code.find('\ndef parse_bulletin', i)
if i < 0 or j < 0:
    sys.exit('Could not locate parse_schedule bounds')

new_sched = r'''def parse_schedule(src):
    if not src:
        return []
    junk_course = re.compile(
        r'^(attendance\s*totals?|totals?|period|course|class|teacher|room|time|'
        r'day|schedule|homeroom\s*attendance|present|absent|tardy)$',
        re.I,
    )
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
            period = None
            for c in cells[:3]:
                if re.fullmatch(r'\d{1,2}[A-Za-z]?', c) or re.fullmatch(r'[A-H]', c) or re.match(r'^P(?:er(?:iod)?)?\s*\d+', c, re.I):
                    period = c
                    break
            if not period:
                continue
            if re.fullmatch(r'0', str(period)):
                continue
            course = ''
            room = ''
            teacher = ''
            times = ''
            for c in cells:
                if c == period:
                    continue
                if re.search(r'\d{1,2}:\d{2}\s*[AaPp][Mm]', c):
                    times = c
                elif re.search(r'\broom\b', c, re.I) or (re.fullmatch(r'(?:Rm:?\s*)?[A-Z]?\d{2,4}[A-Z]?', c, re.I) and len(c) < 14):
                    if not room:
                        room = c
                elif not course and len(c) > 2:
                    course = c
                elif course and not teacher and len(c) > 2 and c not in (times, room, course):
                    if ' ' in c or ',' in c or re.search(r'[A-Za-z]', c):
                        teacher = c
            if not course or junk_course.match(course.strip()):
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

code = code[:i] + new_sched + '\n' + code[j:]
print('replaced parse_schedule')

i = code.find('def parse_bulletin(src):')
j = code.find('\ndef scrape_portal_extras', i)
if i < 0 or j < 0:
    sys.exit('Could not locate parse_bulletin bounds')

new_bull = r'''def parse_bulletin(src):
    if not src:
        return []
    nav = re.compile(
        r'^(home|grades|attendance|schedule|email|logout|my\s*account|'
        r'class\s*pages?|teacher\s*comments?|fee|balance|documents?|'
        r'report\s*cards?|school\s*info|help|print|back|next|previous)$',
        re.I,
    )
    items = []
    seen = set()

    def add(text, title=None, date=None):
        t = strip(text)
        if not t or len(t) < 20:
            return
        if nav.match(t):
            return
        key = t[:80].lower()
        if key in seen:
            return
        seen.add(key)
        item = {'text': t[:500]}
        if title:
            item['title'] = strip(title)[:120]
        if date:
            item['date'] = strip(date)[:40]
        items.append(item)

    for m in re.finditer(
        r'<div\b[^>]*class=["\'][^"\']*(?:bulletin|announcement|message-board|school-news)[^"\']*["\'][^>]*>(.*?)</div>',
        src, re.I|re.S,
    ):
        add(m.group(1))
    for tm in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', src, re.I|re.S):
        cells = [strip(x) for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tm.group(1), re.I|re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        date = None
        for c in cells:
            if re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', c) or re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}', c, re.I):
                date = c
                break
        body = max(cells, key=len)
        if date and body and body != date and len(body) > 25:
            add(body, date=date)
    for m in re.finditer(r'<(?:article|section)\b[^>]*>(.*?)</(?:article|section)>', src, re.I|re.S):
        t = strip(m.group(1))
        if len(t) > 40 and not nav.match(t):
            add(t)
    return items[:15]
'''

code = code[:i] + new_bull + '\n' + code[j:]
print('replaced parse_bulletin')

old_sched_paths = "('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html', 'studentMatrixSchedule.html')"
new_sched_paths = "('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html', 'studentMatrixSchedule.html', 'myScheduleMatrix.html', 'studentScheduleMatrix.html', 'classSchedule.html')"
if old_sched_paths in code:
    code = code.replace(old_sched_paths, new_sched_paths, 1)
    print('expanded schedule paths')

old_bull_paths = "('bulletin_list.html', 'studentbulletin.html', 'bulletin.html', 'schoolbulletin.html')"
new_bull_paths = "('bulletin_list.html', 'studentbulletin.html', 'bulletin.html', 'schoolbulletin.html', 'mybulletin.html', 'bulletinboard.html', 'announcements.html', 'schoolBulletin.html')"
if old_bull_paths in code:
    code = code.replace(old_bull_paths, new_bull_paths, 1)
    print('expanded bulletin paths')

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError:', e)
    sys.exit(1)

path.write_text(code)
print('OK')
