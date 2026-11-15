#!/usr/bin/env python3
"""Polish V2/V3 cards: ungraded show dash (not F); exclude due/summary sensors."""
from pathlib import Path
import urllib.request
import re
import sys

BASE = "https://raw.githubusercontent.com/cjprsnin/powerschool-ha/0281ae0b80e3c2691b241b285b0329052c374711"

def get(path):
    return urllib.request.urlopen(BASE + "/" + path).read().decode()

def patch_v2(t):
    old_is = "_isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming_assignments|grade_average|missing_assignments|late_assignments|ungraded_assignments|assignment_count|course_count|_status$|absences|tardies|absent_days|tardy_days|bulletin|schedule_periods|class_roster/.test(eid))return false;return 'section_id' in a||'missing_homework' in a||'assignment_status' in a;}"
    new_is = "_isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming|grade_average|missing_assignments|late_assignments|ungraded_assignments|graded_assignments|assignment_count|course_count|_status$|absences|tardies|absent_days|tardy_days|bulletin|schedule|roster|grade_history|standards|incomplete|exempt|collected|absent_assignments/.test(eid))return false;return ('section_id' in a)||('missing_homework' in a)||('assignment_status' in a)||Array.isArray(a.assignments);}"
    if old_is not in t:
        sys.exit("v2 isCourse pattern not found")
    t = t.replace(old_is, new_is)
    def repl_letter(m):
        return "const letter=p=>{if(p==null||p===''||isNaN(Number(p)))return '\\u2013';const r=Math.round(Number(p));if(isNaN(r))return '\\u2013';for(const [m,l] of LET)if(r>=m)return l;return 'F';};"
    # use real en-dash character via unicode in write path
    def repl_letter2(m):
        dash = "\u2013"
        return f"const letter=p=>{{if(p==null||p===''||isNaN(Number(p)))return '{dash}';const r=Math.round(Number(p));if(isNaN(r))return '{dash}';for(const [m,l] of LET)if(r>=m)return l;return 'F';}};"
    t2, n = re.subn(
        r"const letter=p=>\{if\(p==null\|\|isNaN\(p\)\)return [^;]+;const r=Math\.round\(p\);for\(const \[m,l\] of LET\)if\(r>=m\)return l;return 'F';\};",
        repl_letter2, t, count=1)
    if not n:
        sys.exit("v2 letter not found")
    t = t2
    needle = "const p=parseFloat(s.state);const col=palette(nm);"
    if needle not in t:
        sys.exit("v2 pct needle not found")
    idx = t.find(needle)
    rest = t[idx:]
    end = rest.find("};")
    old_block = rest[: end + 2]
    dash = "\u2013"
    new_block = (
        "const col=palette(nm);"
        "let p=null;"
        "if(a.grade_percent!=null&&a.grade_percent!==''&&!isNaN(parseFloat(a.grade_percent)))p=parseFloat(a.grade_percent);"
        "else if(s.state!=null&&s.state!==''&&s.state!=='unknown'&&s.state!=='unavailable'){"
        "const ps=parseFloat(s.state);"
        "if(!isNaN(ps)&&(a.grade_letter||a.grade_percent!=null))p=ps;}"
        f"return{{id:s.entity_id,name:nm,pct:p,letter:p==null?'{dash}':letter(p),col,a,"
        "teacher:a.teacher||'',room:a.room||'',trend:this._trend[s.entity_id]||null,"
        "assignments:a.assignments||[]};"
    )
    t = t[:idx] + new_block + t[idx + len(old_block) :]
    return t

def patch_v3(t):
    old_is = "_isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming_assignments|grade_average|missing_assignments|late_assignments|_status$|absences|tardies/.test(eid))return false;return 'section_id' in a||'missing_homework' in a||'assignment_status' in a;}"
    new_is = "_isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming|grade_average|missing_assignments|late_assignments|ungraded_assignments|graded_assignments|assignment_count|course_count|_status$|absences|tardies|absent_days|tardy_days|bulletin|schedule|roster|grade_history|standards|incomplete|exempt|collected|absent_assignments/.test(eid))return false;return ('section_id' in a)||('missing_homework' in a)||('assignment_status' in a)||Array.isArray(a.assignments);}"
    if old_is not in t:
        sys.exit("v3 isCourse pattern not found")
    t = t.replace(old_is, new_is)
    dash = "\u2013"
    def repl_letter2(m):
        return f"const letter=p=>{{if(p==null||p===''||isNaN(Number(p)))return '{dash}';const r=Math.round(Number(p));if(isNaN(r))return '{dash}';for(const [m,l] of LET)if(r>=m)return l;return 'F';}};"
    t2, n = re.subn(
        r"const letter=p=>\{if\(p==null\|\|isNaN\(p\)\)return [^;]+;const r=Math\.round\(p\);for\(const \[m,l\] of LET\)if\(r>=m\)return l;return 'F';\};",
        repl_letter2, t, count=1)
    if not n:
        sys.exit("v3 letter not found")
    t = t2
    helper = "const coursePct=(s,a)=>{if(!a)a={};if(a.grade_percent!=null&&a.grade_percent!==''&&!isNaN(parseFloat(a.grade_percent)))return parseFloat(a.grade_percent);if(s&&s.state!=null&&s.state!==''&&s.state!=='unknown'&&s.state!=='unavailable'){const ps=parseFloat(s.state);if(!isNaN(ps)&&(a.grade_letter||a.grade_percent!=null))return ps;}return null;};\n"
    if "coursePct=" not in t:
        t = t.replace(
            "const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');",
            "const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');\n" + helper,
        )
    t = t.replace(
        "const gs=states.map(s=>parseFloat(s.state)).filter(n=>!isNaN(n));return gs.length?gs.reduce((a,b)=>a+b,0)/gs.length:null;}",
        "const gs=states.map(s=>coursePct(s,s.attributes||{})).filter(n=>n!=null);return gs.length?gs.reduce((a,b)=>a+b,0)/gs.length:null;}",
    )
    t = t.replace(
        "const g=parseFloat(s.state);const [c1,c2]=palette(nm);const dir=this._trend[s.entity_id];",
        "const g=coursePct(s,a);const [c1,c2]=palette(nm);const dir=this._trend[s.entity_id];",
    )
    t = t.replace(
        "const grade=s?parseFloat(s.state):null;const [c1,c2]=palette(nm);",
        "const grade=s?coursePct(s,a):null;const [c1,c2]=palette(nm);",
    )
    return t

def main():
    root = Path(".")
    www = root / "www"
    www.mkdir(exist_ok=True)
    v2 = patch_v2(get("www/powerschool-v2-card.js"))
    v3 = patch_v3(get("www/powerschool-v3-card.js"))
    (www / "powerschool-v2-card.js").write_text(v2)
    (www / "powerschool-v3-card.js").write_text(v3)
    print("OK v2", len(v2), "v3", len(v3))

if __name__ == "__main__":
    main()
