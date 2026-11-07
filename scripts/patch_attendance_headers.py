#!/usr/bin/env python3
"""Patch client_body.py attendance header matching for multi-row PowerSchool tables."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
if not path.exists():
    sys.exit(f"Missing {path} — run from powerschool-ha repo root")

code = path.read_text()
start = code.find("    def _header_label(")
end = code.find("    output=[]\n    for i,row in enumerate(rows):")
if start < 0 or end < 0:
    sys.exit("Could not find header block to replace (already patched?)")

new = r'''    def _header_label(attrs_str, cell_inner):
        """Searchable label from cell text + title/alt/aria (not raw attrs)."""
        parts=[]
        t=strip(cell_inner)
        if t:
            parts.append(t)
        blob=(attrs_str or '')+' '+(cell_inner or '')
        for attr in ('title','aria-label','alt','data-label','data-original-title'):
            m=re.search(r'\b'+attr+r'\s*=\s*["\']([^"\']+)["\']', blob, re.I)
            if m:
                parts.append(strip(m.group(1)))
        for m in re.finditer(r'<img\b[^>]*>', cell_inner or '', re.I):
            alt=re.search(r'\balt\s*=\s*["\']([^"\']+)["\']', m.group(0), re.I)
            if alt:
                parts.append(strip(alt.group(1)))
        return norm(' '.join(parts))

    def _extract_header_row(row_html):
        labels=[]
        for m in re.finditer(r'<(th|td)\b([^>]*)>(.*?)</\1>', row_html, re.I|re.S):
            label=_header_label(m.group(2), m.group(3))
            colspan=intval(attrs(m.group(2)).get('colspan')) or 1
            # Do not expand week-group colspans — they push Absences past data cells.
            if not label and colspan > 1:
                labels.extend(['']*colspan)
            else:
                labels.append(label)
        return labels

    def _score_header_row(labels):
        blob=' '.join(labels).lower()
        score=0
        if re.search(r'\babsences?\b', blob): score += 5
        if re.search(r'\btardies?\b', blob): score += 5
        if re.search(r'\bcourse\b', blob): score += 3
        if re.search(r'\b(exp|y1|t1|t2|t3)\b', blob): score += 2
        if re.search(r'last week|this week|colspan|rowspan|scope=', blob): score -= 4
        return score

    header_values=[]
    candidates=[]
    hm=re.search(r'<caption\b[^>]*\bid=["\']attByClass["\'][^>]*>.*?</caption>',src,re.I|re.S)
    search_from=src[hm.end():] if hm else src
    for tm in re.finditer(r'<tr\b[^>]*>(.*?)</tr>', search_from, re.I|re.S):
        labels=_extract_header_row(tm.group(1))
        if len(labels) < 2:
            continue
        candidates.append(labels)
        if len(candidates) >= 8:
            break
    if candidates:
        ranked=sorted(candidates, key=_score_header_row, reverse=True)
        if _score_header_row(ranked[0]) > 0:
            header_values=ranked[0]
    if not header_values:
        for labels in candidates:
            blob=' '.join(labels).lower()
            if 'course' in blob or 'abs' in blob:
                header_values=labels
                break
    debug('attByClass headers: %s' % json.dumps(header_values,ensure_ascii=False))

    def _header_index(patterns, exclude=None):
        exclude = exclude or []
        for i,h in enumerate(header_values):
            hl=(h or '').lower()
            if any(re.search(ex, hl) for ex in exclude):
                continue
            for pat in patterns:
                if re.search(pat, hl):
                    return i
        return None

    abs_idx=_header_index([
        r'^absences?$',
        r'^abs$',
        r'^absent$',
        r'\babsences?\b',
    ], exclude=[r'assignment', r'classwork', r'week'])
    tardy_idx=_header_index([
        r'^tardies?$',
        r'^tardy$',
        r'^tdy$',
        r'\btardies?\b',
    ], exclude=[r'start', r'student', r'week'])
    att_idx=_header_index([r'^att$', r'^attend$', r'^attendance$'], exclude=[r'pattern', r'code', r'week'])
    debug('attendance column indexes: absences=%s tardies=%s att=%s headers=%d' % (
        abs_idx, tardy_idx, att_idx, len(header_values)))

'''

code = code[:start] + new + code[end:]

old = """        absences=_cell_count(abs_idx)
        tardies=_cell_count(tardy_idx)
        if absences is None and att_idx is not None and abs_idx is None:
            absences=_cell_count(att_idx)
"""
new_c = """        use_abs, use_tardy, use_att = abs_idx, tardy_idx, att_idx
        nvals=len(values)
        if (use_abs is not None and use_abs >= nvals) or (use_tardy is not None and use_tardy >= nvals):
            if nvals >= 2 and abs_idx is not None and tardy_idx is not None:
                use_abs, use_tardy = nvals-2, nvals-1
            elif nvals >= 1 and abs_idx is not None:
                use_abs = nvals-1
        absences=_cell_count(use_abs)
        tardies=_cell_count(use_tardy)
        if absences is None and use_att is not None and use_abs is None:
            absences=_cell_count(use_att if use_att < nvals else nvals-1)
"""
if old not in code:
    if "use_abs, use_tardy, use_att" in code:
        print("cell fallback already present")
    else:
        sys.exit("cell count block not found")
else:
    code = code.replace(old, new_c, 1)

compile(code, "client_body.py", "exec")
path.write_text(code)
print("Patched", path)
