#!/usr/bin/env python3
"""Filter junk schedule headers and nav chrome from bulletin items."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text(encoding="utf-8")
if "POWERSCHOOL_SCHED_FILTER_V1" in code:
    print("already applied")
    sys.exit(0)

old_sched_tail = """    seen = set()
    out = []
    for r in rows:
        key = (r['period'], r['course'])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
"""

old_sched_tail2 = """    seen = set()
    out = []
    for r in rows:
        key = (r.get('period'), (r.get('course') or '').lower())
        if key in seen or not r.get('course'):
            continue
        seen.add(key)
        out.append(r)
    return out
"""

new_sched_tail = """    # POWERSCHOOL_SCHED_FILTER_V1
    junk_name = re.compile(
        r'^(day|terms?|con|exp|period|course|class|teacher|room|time|schedule|'
        r'week|this\\s*week|last\\s*week|homeroom\\s*attendance|'
        r'k?am|k?pm|k?lr|\\d{1,2}(?:am|pm|lr)|p(?:am|pm)|'
        r'mon(day)?|tue(s(day)?)?|wed(nesday)?|thu(rs(day)?)?|fri(day)?)$',
        re.I,
    )
    seen = set()
    out = []
    for r in rows:
        course = (r.get('course') or '').strip()
        if not course:
            continue
        if junk_name.match(course):
            continue
        if re.fullmatch(r'[A-Z]?\\d{0,2}[A-Z]{0,3}', course, re.I) and len(course) <= 4:
            if not r.get('room') and not r.get('teacher'):
                continue
        has_meta = bool(r.get('room') or r.get('teacher') or r.get('period') or r.get('time'))
        if not has_meta and (' ' not in course and len(course) < 8):
            continue
        cleaned = clean_course_name(course) or course
        if cleaned and cleaned != course and len(cleaned) >= 3:
            r = dict(r)
            tch, rm = parse_course_meta(course)
            if tch and not r.get('teacher'):
                r['teacher'] = tch
            if rm and not r.get('room'):
                r['room'] = rm
            r['course'] = cleaned
            course = cleaned
        if junk_name.match(course):
            continue
        key = (r.get('period'), course.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
"""

applied = False
for old in (old_sched_tail, old_sched_tail2):
    if old in code:
        code = code.replace(old, new_sched_tail, 1)
        applied = True
        print("schedule filter attached")
        break
if not applied:
    sys.exit("could not find schedule dedupe tail to patch")

nav_old = """    nav = re.compile(
        r'^(home|grades|attendance|schedule|email|logout|my\\s*account|'
        r'class\\s*pages?|teacher\\s*comments?|fee|balance|documents?|'
        r'report\\s*cards?|school\\s*info|help|print|back|next|previous)$',
        re.I,
    )
"""
nav_new = """    nav = re.compile(
        r'^(home|grades|attendance|schedule|email|logout|my\\s*account|'
        r'class\\s*pages?|teacher\\s*comments?|fee|balance|documents?|'
        r'report\\s*cards?|school\\s*info|help|print|back|next|previous|'
        r'school\\s*bulletin|announcements?|bulletin|'
        r'grades\\s+and\\s+attendance(?:\\s+\\w+)?|attendance\\s+history|'
        r'email\\s+notification|class\\s+registration|account\\s+preferences|'
        r'welcome[,\\s]+.+|school\\s+information)$',
        re.I,
    )
"""
if nav_old in code:
    code = code.replace(nav_old, nav_new, 1)
    print("bulletin nav filter expanded")
else:
    print("nav regex not exact — skip expand")

new_ret = """    cleaned = []
    for it in items:
        t = (it.get('text') or '')
        if re.search(r'forms_teacher_portal|left_navigation|["\']\\s*\\+\\s*["\']', t, re.I):
            continue
        if nav.match(t):
            continue
        cleaned.append(it)
    return cleaned[:15]
"""
bi = code.find("def parse_bulletin(")
bj = code.find("\\ndef scrape_portal_extras", bi)
if bj < 0:
    bj = code.find("\\ndef ", bi + 10)
block = code[bi:bj]
if "forms_teacher_portal" not in block or "cleaned = []" not in block:
    if "return items[:15]\\n" in block:
        code = code[:bi] + block.replace("    return items[:15]\\n", new_ret, 1) + code[bj:]
        print("bulletin return filter")
    elif "return items[:20]\\n" in block:
        code = code[:bi] + block.replace("    return items[:20]\\n", new_ret, 1) + code[bj:]
        print("bulletin return filter 20")
    else:
        print("bulletin return not found")

try:
    compile(code, "client_body.py", "exec")
except SyntaxError as e:
    print("SyntaxError", e)
    sys.exit(1)

path.write_text(code, encoding="utf-8")
print("OK")
