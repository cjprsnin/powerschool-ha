#!/usr/bin/env python3
"""Phase 2: term-column grades (T1/T2/Y1), standards levels, prior-term attributes."""
from pathlib import Path
import sys
import re

ROOT = Path('custom_components/powerschool')
client = ROOT / 'client_body.py'
sensor = ROOT / 'sensor.py'
const = ROOT / 'const.py'

if not client.exists():
    sys.exit('Run from repo root')

code = client.read_text()
changes = 0

# --- 1. Expand grade_value for standards ---
old_gv_end = "    m=re.fullmatch(r'([A-F][+-]?)',t,re.I)\n    if m:return {'raw':t,'percent':None,'letter':m.group(1).upper()}\n    return {'raw':t,'percent':None,'letter':None}"

new_gv_end = """    m=re.fullmatch(r'([A-F][+-]?)',t,re.I)
    if m:return {'raw':t,'percent':None,'letter':m.group(1).upper(),'scale':'letter'}
    # Elementary / standards proficiency scales
    m=re.fullmatch(r'([1-4])',t)
    if m:return {'raw':t,'percent':None,'letter':None,'level':m.group(1),'scale':'standards'}
    m=re.fullmatch(r'(E|M|S|N|ES|MS|NY|ME|EX|PR|BG|ND)',t,re.I)
    if m:return {'raw':t,'percent':None,'letter':m.group(1).upper(),'level':m.group(1).upper(),'scale':'standards'}
    if re.fullmatch(r'[A-Za-z0-9.+\\-]{1,6}', t):
        return {'raw':t,'percent':None,'letter':None,'level':t,'scale':'other'}
    return {'raw':t,'percent':None,'letter':None}"""

if old_gv_end in code and "scale':'standards'" not in code:
    code = code.replace(old_gv_end, new_gv_end, 1)
    code = code.replace(
        "return {'raw':t,'earned':None,'possible':None,'percent':pct,'letter':letter}",
        "return {'raw':t,'earned':None,'possible':None,'percent':pct,'letter':letter,'scale':'letter'}",
        1,
    )
    changes += 1
    print('expanded grade_value for standards')
elif "scale':'standards'" in code:
    print('grade_value already expanded')
else:
    print('WARN: grade_value end block not matched')

# --- 2. term column map after attendance debug ---
needle = "debug('attendance column indexes: absences=%s tardies=%s att=%s headers=%d' % (\n        abs_idx, tardy_idx, att_idx, len(header_values)))"
insert_after = needle + """

    term_cols={}
    for hi,h in enumerate(header_values):
        hl=re.sub(r'\\s+','', (h or '').strip().upper())
        if re.fullmatch(r'(T|Q|S|P)\\d+|Y1|S1|S2|SEM\\d?', hl):
            term_cols[hl]=hi
    if term_cols:
        debug('term columns: %s' % term_cols)"""

if 'term_cols={}' not in code and needle in code:
    code = code.replace(needle, insert_after, 1)
    changes += 1
    print('added term_cols mapping')
elif 'term_cols={}' in code:
    print('term_cols already present')
else:
    print('WARN: attendance debug needle not found')

# --- 3. Per-row term_grades ---
old_g = "        g=grade_value(grade_raw)"
new_g = """        # Term / report-card style columns (T1, T2, Y1, ...)
        term_grades={}
        for tcode, tidx in term_cols.items():
            if tidx is None or tidx >= len(values):
                continue
            raw=values[tidx]
            if not raw or raw in ('','-','--','—','N/A','n/a','.'):
                continue
            tg=grade_value(raw)
            term_grades[tcode]=tg
        # Prefer current-looking term cell when score link had no grade text
        if not grade_raw and term_grades:
            for prefer in ('T1','T2','T3','T4','Q1','Q2','Q3','Q4','S1','S2','Y1'):
                if prefer in term_grades and term_grades[prefer].get('raw'):
                    grade_raw=term_grades[prefer]['raw']
                    break
            if not grade_raw:
                for prefer in sorted(term_grades.keys()):
                    if term_grades[prefer].get('raw'):
                        grade_raw=term_grades[prefer]['raw']
                        break
        g=grade_value(grade_raw)"""

if 'term_grades={}' not in code and old_g in code:
    code = code.replace(old_g, new_g, 1)
    changes += 1
    print('added per-row term_grades')
elif 'term_grades={}' in code:
    print('term_grades already present')
else:
    print('WARN: g=grade_value needle not found')

# --- 4. output dict ---
old_out = """        output.append({
            'course':course,
            'grade_raw':grade_raw,
            'grade_percent':g.get('percent'),
            'grade_letter':g.get('letter'),
            'links':links,
            'section_id':section_id,
            'row_id':row_id,
            'row_attrs':dict(row.get('attrs',{})),
            'cell_attrs':[dict(c.get('attrs',{})) for c in row.get('cells',[])],
            'absences':absences,
            'tardies':tardies,
        })"""

new_out = """        output.append({
            'course':course,
            'grade_raw':grade_raw,
            'grade_percent':g.get('percent'),
            'grade_letter':g.get('letter'),
            'grade_level':g.get('level'),
            'grade_scale':g.get('scale'),
            'term_grades':{k:{'raw':v.get('raw'),'percent':v.get('percent'),'letter':v.get('letter'),'level':v.get('level'),'scale':v.get('scale')} for k,v in term_grades.items()},
            'links':links,
            'section_id':section_id,
            'row_id':row_id,
            'row_attrs':dict(row.get('attrs',{})),
            'cell_attrs':[dict(c.get('attrs',{})) for c in row.get('cells',[])],
            'absences':absences,
            'tardies':tardies,
        })"""

if "'term_grades':" not in code and old_out in code:
    code = code.replace(old_out, new_out, 1)
    changes += 1
    print('output includes term_grades')
elif "'term_grades':" in code:
    print('term_grades in output already')
else:
    print('WARN: output.append block not matched')

# --- 5. process_student bulk keys ---
bulk_old = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','section_id','absences','tardies')}"
bulk_new = "cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','grade_level','grade_scale','term_grades','section_id','absences','tardies')}"
if bulk_old in code:
    code = code.replace(bulk_old, bulk_new, 1)
    changes += 1
    print('process_student bulk keys include term_grades')
elif bulk_new in code:
    print('process_student bulk keys already updated')
else:
    print('WARN: could not auto-wire process_student term_grades')

try:
    compile(code, 'client_body.py', 'exec')
except SyntaxError as e:
    print('SyntaxError:', e)
    sys.exit(1)

client.write_text(code)
print('client_body patched, changes=', changes)

# --- sensor ---
s = sensor.read_text()
sc = 0

old_nv = '''    @property
    def native_value(self):
        course = self._course()
        if course.get("grade_percent") is not None:
            return course.get("grade_percent")
        return course.get("grade_letter") or course.get("grade_raw") or None'''

new_nv = '''    @property
    def native_value(self):
        course = self._course()
        if course.get("grade_percent") is not None:
            return course.get("grade_percent")
        if course.get("grade_letter"):
            return course.get("grade_letter")
        if course.get("grade_level"):
            return course.get("grade_level")
        tg = course.get("term_grades") or {}
        for prefer in ("T1", "T2", "T3", "T4", "Q1", "Q2", "Q3", "Q4", "S1", "S2", "Y1"):
            cell = tg.get(prefer) or {}
            if cell.get("letter") or cell.get("level") or cell.get("raw"):
                return cell.get("letter") or cell.get("level") or cell.get("raw")
        return course.get("grade_raw") or None'''

if old_nv in s:
    s = s.replace(old_nv, new_nv, 1)
    sc += 1
    print('sensor native_value supports standards/term')
else:
    print('WARN: native_value block not matched')

marker = '            "absences": course.get("absences"),\n            "tardies": course.get("tardies"),\n        }'
if marker in s:
    s = s.replace(
        marker,
        '            "absences": course.get("absences"),\n'
        '            "tardies": course.get("tardies"),\n'
        '            "grade_level": course.get("grade_level"),\n'
        '            "grade_scale": course.get("grade_scale"),\n'
        '            "term_grades": course.get("term_grades") or {},\n'
        '        }',
        1,
    )
    sc += 1
    print('sensor attrs include term_grades')
else:
    print('WARN: course attrs marker not found')

sensor.write_text(s)
print('sensor changes=', sc)

c = const.read_text()
if 'standards_course_count' not in c:
    needle = '    "bulletin_count": ("Bulletin Items", None, True),'
    if needle in c:
        const.write_text(c.replace(
            needle,
            needle + '\n    "standards_course_count": ("Standards Courses", None, True),',
            1,
        ))
        print('const: standards_course_count')
print('OK')
