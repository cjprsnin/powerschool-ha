#!/usr/bin/env python3
"""Inject schedule / day-attendance / bulletin scrapers into client_body.py and wire sensors."""
from pathlib import Path
import sys

EXTRAS = r'''
def _guardian(path):
    return urljoin(HOME_URL, path)

def fetch_html(path_or_url):
    url = path_or_url if str(path_or_url).startswith('http') else _guardian(path_or_url)
    r = get(url)
    if r.get('status', 500) >= 400:
        return None, url, r.get('status')
    return r.get('body') or '', url, r.get('status')

def parse_schedule(src):
    if not src:
        return []
    rows = []
    for tm in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', src, re.I|re.S):
        cells = [strip(x) for x in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tm.group(1), re.I|re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            continue
        blob = ' '.join(cells).lower()
        if 'period' in blob and ('course' in blob or 'class' in blob) and len(cells) >= 3:
            continue
        period = None
        for c in cells[:3]:
            if re.fullmatch(r'\d{1,2}[A-Za-z]?', c) or re.fullmatch(r'[A-H]', c) or re.match(r'^P(?:er(?:iod)?)?\s*\d+', c, re.I):
                period = c
                break
        if not period:
            continue
        course = ''
        room = ''
        teacher = ''
        times = ''
        for c in cells:
            if re.search(r'\d{1,2}:\d{2}\s*[AaPp][Mm]', c):
                times = c
            elif re.search(r'\broom\b', c, re.I) or (re.fullmatch(r'[A-Z]?\d{2,4}[A-Z]?', c) and len(c) < 12):
                if not room:
                    room = c
            elif not course and len(c) > 3 and c != period:
                course = c
            elif course and not teacher and len(c) > 3 and c not in (period, times, room, course):
                teacher = c
        if course:
            rows.append({'period': period, 'course': course, 'teacher': teacher or None, 'room': room or None, 'time': times or None})
    return rows

def parse_attendance_days(src):
    if not src:
        return {'days': [], 'codes': {}, 'absent_days': 0, 'tardy_days': 0, 'status': 'unavailable'}
    days = []
    codes = {}
    for m in re.finditer(
        r'(?P<date>\b(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b).{0,100}?(?P<code>\b(?:[EUTAX]|UA|EA|TDY|ABS|T)\b)',
        src, re.I|re.S,
    ):
        date = m.group('date')
        code = m.group('code').upper()
        days.append({'date': date, 'code': code})
        codes[code] = codes.get(code, 0) + 1
    seen = set()
    uniq = []
    for d in days:
        if d['date'] in seen:
            continue
        seen.add(d['date'])
        uniq.append(d)
    absent_days = sum(1 for d in uniq if d['code'] in ('A', 'U', 'E', 'X', 'ABS', 'UA', 'EA') or d['code'].startswith('A'))
    tardy_days = sum(1 for d in uniq if d['code'] in ('T', 'TDY') or d['code'].startswith('T'))
    return {'days': uniq[:120], 'codes': codes, 'absent_days': absent_days, 'tardy_days': tardy_days, 'status': 'ok' if uniq else 'unavailable'}

def parse_bulletin(src):
    if not src:
        return []
    items = []
    for m in re.finditer(r'<div\b[^>]*class=["\'][^"\']*bulletin[^"\']*["\'][^>]*>(.*?)</div>', src, re.I|re.S):
        t = strip(m.group(1))
        if t and len(t) > 10:
            items.append({'text': t[:500]})
    if not items:
        for m in re.finditer(r'<li\b[^>]*>(.*?)</li>', src, re.I|re.S):
            t = strip(m.group(1))
            if t and len(t) > 25:
                items.append({'text': t[:500]})
            if len(items) >= 15:
                break
    return items[:15]

def scrape_portal_extras():
    schedule, schedule_status = [], 'unavailable'
    for path in ('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html'):
        body, url, status = fetch_html(path)
        if not body:
            continue
        rows = parse_schedule(body)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from %s rows=%s' % (url, len(rows)))
            break
    attendance = {'days': [], 'codes': {}, 'absent_days': None, 'tardy_days': None, 'status': 'unavailable'}
    for path in ('attendance.html', 'meets.html', 'studentAttendance.html', 'attendanceHistory.html', 'monthcalendar.html'):
        body, url, status = fetch_html(path)
        if not body:
            continue
        parsed = parse_attendance_days(body)
        if parsed.get('days'):
            attendance = parsed
            debug('attendance days from %s count=%s' % (url, len(parsed['days'])))
            break
    bulletin, bulletin_status = [], 'unavailable'
    for path in ('bulletin_list.html', 'studentbulletin.html', 'bulletin.html', 'schoolbulletin.html'):
        body, url, status = fetch_html(path)
        if not body:
            continue
        items = parse_bulletin(body)
        if items:
            bulletin, bulletin_status = items, 'ok'
            debug('bulletin from %s items=%s' % (url, len(items)))
            break
    return {
        'schedule': schedule,
        'schedule_status': schedule_status,
        'schedule_count': len(schedule),
        'attendance_days': attendance.get('days') or [],
        'attendance_codes': attendance.get('codes') or {},
        'absent_days': attendance.get('absent_days'),
        'tardy_days': attendance.get('tardy_days'),
        'attendance_day_status': attendance.get('status', 'unavailable'),
        'bulletin': bulletin,
        'bulletin_status': bulletin_status,
        'bulletin_count': len(bulletin),
    }
'''

def main():
    path = Path('custom_components/powerschool/client_body.py')
    if not path.exists():
        sys.exit('Run from repo root')
    code = path.read_text()

    bad = "debug('No course rows/links found for %s. Student remains valid.'%name);try:"
    if bad in code:
        print('Detected broken client_body.py — restore first:')
        print('  git checkout -- custom_components/powerschool/client_body.py')
        print('  python3 scripts/patch_portal_extras.py')
        sys.exit(2)

    if 'def scrape_portal_extras' not in code:
        marker = 'def process_student('
        if marker not in code:
            sys.exit('process_student not found')
        code = code.replace(marker, EXTRAS + '\n\ndef process_student(', 1)

    idx = code.find('def process_student(')
    end = code.find('\ndef main(', idx)
    if idx < 0 or end < 0:
        sys.exit('process_student / main bounds not found')
    block = code[idx:end]

    if 'scrape_portal_extras()' not in block:
        target = '\n    return result\n'
        inject = '''
    try:
        extras = scrape_portal_extras()
        result.update(extras)
    except Exception as _ex:
        debug('portal extras failed: %s' % _ex)
        result.setdefault('schedule_status', 'unavailable')
        result.setdefault('attendance_day_status', 'unavailable')
        result.setdefault('bulletin_status', 'unavailable')
    return result
'''
        if target not in block:
            if block.rstrip().endswith('return result'):
                lines = block.splitlines(keepends=True)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == 'return result' and lines[i].startswith('    return'):
                        lines[i] = inject if inject.endswith('\n') else inject + '\n'
                        block = ''.join(lines)
                        break
                else:
                    sys.exit('Could not find standalone return result')
            else:
                sys.exit('Could not find standalone return result to inject extras')
        else:
            pos = block.rfind(target)
            block = block[:pos] + inject + block[pos + len(target):]
        code = code[:idx] + block + code[end:]

    try:
        compile(code, 'client_body.py', 'exec')
    except SyntaxError as e:
        print('SyntaxError after patch:', e)
        sys.exit(1)

    path.write_text(code)
    print('Patched client_body.py')

    const = Path('custom_components/powerschool/const.py')
    c = const.read_text()
    if 'absent_days' not in c:
        needle = '    "due_soon_count": ("Due Soon Assignments", None, False),'
        add = needle + '''
    "schedule_count": ("Schedule Periods", None, True),
    "absent_days": ("Absent Days", None, False),
    "tardy_days": ("Tardy Days", None, False),
    "bulletin_count": ("Bulletin Items", None, True),'''
        if needle not in c:
            sys.exit('const needle not found')
        const.write_text(c.replace(needle, add, 1))
        print('Patched const.py')
    else:
        print('const already has absent_days')

    sensor = Path('custom_components/powerschool/sensor.py')
    s = sensor.read_text()
    if 'attendance_days' not in s:
        old = '''        elif self._field in ("absences", "tardies"):
            attrs["attendance_status"] = student.get("attendance_status")
            attrs["by_course"] = student.get("attendance_by_course") or []
            attrs["attendance_headers"] = student.get("attendance_headers") or []
            attrs["attendance_abs_column"] = student.get("attendance_abs_column")
            attrs["attendance_tardy_column"] = student.get("attendance_tardy_column")
'''
        new = old + '''        elif self._field in ("absent_days", "tardy_days"):
            attrs["attendance_day_status"] = student.get("attendance_day_status")
            attrs["attendance_days"] = student.get("attendance_days") or []
            attrs["attendance_codes"] = student.get("attendance_codes") or {}
        elif self._field == "schedule_count":
            attrs["schedule_status"] = student.get("schedule_status")
            attrs["schedule"] = student.get("schedule") or []
        elif self._field == "bulletin_count":
            attrs["bulletin_status"] = student.get("bulletin_status")
            attrs["bulletin"] = student.get("bulletin") or []
'''
        if old not in s:
            sys.exit('sensor block not found')
        sensor.write_text(s.replace(old, new, 1))
        print('Patched sensor.py')
    else:
        print('sensor already has attendance_days')
    print('OK')

if __name__ == '__main__':
    main()
