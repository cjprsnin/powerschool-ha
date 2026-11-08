#!/usr/bin/env python3
"""Improve portal extras: home_src for schedule/bulletin, fix attendance_codes counts."""
from pathlib import Path
import sys

path = Path('custom_components/powerschool/client_body.py')
code = path.read_text()
if 'def scrape_portal_extras' not in code:
    sys.exit('scrape_portal_extras missing — run scripts/patch_portal_extras.py first')

changes = 0

old = """    absent_days = sum(1 for d in uniq if d['code'] in ('A', 'U', 'E', 'X', 'ABS', 'UA', 'EA') or d['code'].startswith('A'))
    tardy_days = sum(1 for d in uniq if d['code'] in ('T', 'TDY') or d['code'].startswith('T'))
    return {'days': uniq[:120], 'codes': codes, 'absent_days': absent_days, 'tardy_days': tardy_days, 'status': 'ok' if uniq else 'unavailable'}"""
new = """    # Recount codes from unique days only (not every HTML match)
    codes = {}
    for d in uniq:
        codes[d['code']] = codes.get(d['code'], 0) + 1
    absent_days = sum(1 for d in uniq if d['code'] in ('A', 'U', 'E', 'X', 'ABS', 'UA', 'EA') or d['code'].startswith('A'))
    tardy_days = sum(1 for d in uniq if d['code'] in ('T', 'TDY') or d['code'].startswith('T'))
    return {'days': uniq[:120], 'codes': codes, 'absent_days': absent_days, 'tardy_days': tardy_days, 'status': 'ok' if uniq else 'unavailable'}"""
if old in code and 'Recount codes from unique' not in code:
    code = code.replace(old, new, 1)
    changes += 1
    print('fixed attendance_codes recount')

old = "def scrape_portal_extras():\n    schedule, schedule_status = [], 'unavailable'"
new = """def scrape_portal_extras(home_src=None):
    schedule, schedule_status = [], 'unavailable'
    if home_src:
        rows = parse_schedule(home_src)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from home.html rows=%s' % len(rows))"""
if old in code:
    code = code.replace(old, new, 1)
    changes += 1
    print('updated scrape_portal_extras signature')

old = """    for path in ('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html'):
        body, url, status = fetch_html(path)
        if not body:
            continue
        rows = parse_schedule(body)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from %s rows=%s' % (url, len(rows)))
            break"""
new = """    if schedule_status != 'ok':
        for path in ('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html', 'studentMatrixSchedule.html'):
            body, url, status = fetch_html(path)
            if not body:
                continue
            rows = parse_schedule(body)
            if rows:
                schedule, schedule_status = rows, 'ok'
                debug('schedule from %s rows=%s' % (url, len(rows)))
                break"""
if old in code:
    code = code.replace(old, new, 1)
    changes += 1
    print('updated schedule loop')

old = """    bulletin, bulletin_status = [], 'unavailable'
    for path in ('bulletin_list.html', 'studentbulletin.html', 'bulletin.html', 'schoolbulletin.html'):"""
new = """    bulletin, bulletin_status = [], 'unavailable'
    if home_src:
        items = parse_bulletin(home_src)
        if items:
            bulletin, bulletin_status = items, 'ok'
            debug('bulletin from home.html items=%s' % len(items))
    for path in ('bulletin_list.html', 'studentbulletin.html', 'bulletin.html', 'schoolbulletin.html'):"""
if old in code:
    code = code.replace(old, new, 1)
    changes += 1
    print('bulletin tries home first')

old = "        extras = scrape_portal_extras()"
new = "        extras = scrape_portal_extras(home_src=src)"
if old in code:
    code = code.replace(old, new, 1)
    changes += 1
    print('wired home_src=src')
elif 'scrape_portal_extras(home_src=src)' in code:
    print('home_src already wired')

if changes == 0 and 'scrape_portal_extras(home_src=src)' in code and 'Recount codes from unique' in code:
    print('Already up to date')
    sys.exit(0)

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError:', e)
    sys.exit(1)

path.write_text(code)
print('Patched client_body.py (%d changes)' % changes)
