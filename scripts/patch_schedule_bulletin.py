#!/usr/bin/env python3
"""Surgical improvements to parse_schedule + parse_bulletin."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text(encoding="utf-8")
if "POWERSCHOOL_SCHED_V2" in code:
    print("already applied")
    sys.exit(0)

if "def parse_schedule(" not in code or "def parse_bulletin(" not in code:
    sys.exit("parse_schedule/parse_bulletin missing")

old_period_gate = """            if not period:
                continue
            course = ''
            room = ''
            teacher = ''
            times = ''
            for c in cells:
                if c == period:
                    continue
"""

new_period_gate = """            # POWERSCHOOL_SCHED_V2: matrix rows without a leading period cell
            if not period:
                course_cells = []
                for c in cells:
                    if len(c) < 3:
                        continue
                    if re.fullmatch(r'\\d{2}-\\d{2}', c):
                        continue
                    if re.fullmatch(r'\\d{1,2}', c) or re.fullmatch(r'P(?:er(?:iod)?)?\\s*\\d{1,2}', c, re.I):
                        continue
                    if re.fullmatch(r'(?:Rm:?\\s*)?[A-Z]?\\d{1,4}[A-Z]?', c, re.I) and len(c) < 10:
                        continue
                    if re.search(r'\\d{1,2}:\\d{2}\\s*[AaPp][Mm]', c):
                        continue
                    if re.fullmatch(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*', c, re.I):
                        continue
                    course_cells.append(c)
                for c in course_cells:
                    name = clean_course_name(c) or c
                    if not name or len(name) < 3:
                        continue
                    tch, rm = parse_course_meta(c)
                    rows.append({
                        'period': None,
                        'course': name,
                        'teacher': tch,
                        'room': rm,
                        'time': None,
                    })
                continue
            course = ''
            room = ''
            teacher = ''
            times = ''
            for c in cells:
                if c == period:
                    continue
"""

if old_period_gate not in code:
    print("period gate block not found — checking variants")
    idx = code.find("if not period:")
    print("first if not period at", idx)
    sys.exit("could not find period gate to patch")

code = code.replace(old_period_gate, new_period_gate, 1)

old_add = """    def add(text, title=None, date=None):
        t = strip(text)
        if not t or len(t) < 20:
            return
        if nav.match(t):
            return
"""
new_add = """    def add(text, title=None, date=None):
        t = strip(text)
        if not t:
            return
        min_len = 12 if title else 18
        if len(t) < min_len:
            return
        if nav.match(t):
            return
"""
if old_add in code:
    code = code.replace(old_add, new_add, 1)
    print("bulletin min_len updated")
else:
    print("bulletin add() block not found (skip)")

li_snip = """    for m in re.finditer(r'<li\\b[^>]*>(.*?)</li>', src, re.I|re.S):
        inner = m.group(1)
        t = strip(inner)
        if len(t) >= 18 and not nav.match(t):
            add(inner)

"""
bull = code.find("def parse_bulletin(")
if bull < 0:
    sys.exit("parse_bulletin missing")
pos = code.find("    for tm in re.finditer(r'<tr\\b[^>]*>(.*?)</tr>', src, re.I|re.S):", bull)
if pos > 0 and "<li\\b" not in code[bull:pos+200]:
    code = code[:pos] + li_snip + code[pos:]
    print("li bulletin parser inserted")
else:
    print("li insert skipped", pos)

old_is = """    def is_period(c):
        c = (c or '').strip()
        if re.fullmatch(r'\\d{1,2}', c):
            return c != '0'
        if re.fullmatch(r'P(?:er(?:iod)?)?\\s*\\d{1,2}', c, re.I):
            return True
        if re.fullmatch(r'\\d{1,2}[A-Za-z]', c):
            return True
        return False
"""
new_is = """    def is_period(c):
        c = (c or '').strip()
        if re.fullmatch(r'\\d{1,2}', c):
            return c != '0'
        if re.fullmatch(r'P(?:er(?:iod)?)?\\s*\\d{1,2}', c, re.I):
            return True
        if re.fullmatch(r'\\d{1,2}[A-Za-z]', c):
            return True
        if re.fullmatch(r'Exp\\.?', c, re.I):
            return True
        return False
"""
if old_is in code:
    code = code.replace(old_is, new_is, 1)
    print("Exp period accepted")
else:
    print("is_period block not exact (ok if photo-cache reformatted)")

try:
    compile(code, "client_body.py", "exec")
except SyntaxError as e:
    print("SyntaxError", e)
    sys.exit(1)

path.write_text(code, encoding="utf-8")
print("applied schedule/bulletin surgical patch")
print("OK")
