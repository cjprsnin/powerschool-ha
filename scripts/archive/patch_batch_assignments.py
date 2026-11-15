#!/usr/bin/env python3
"""Batch multi-section /assignment/lookup + keep DELAY 0.05.

Replaces the per-course assignment loop in process_student with:
  1) build course shells
  2) one POST for all known section_ids when student_dcid is known
  3) fall back to per-course score-page / direct lookup only when needed
"""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
cb = p.read_text(encoding="utf-8")

cb = cb.replace(
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','.25'))",
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','0.05'))",
)
cb = cb.replace(
    "DELAY=0.25",
    'DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))',
)

marker = "def fetch_assignments(score_url,student_id,debug_tag='course',section_id=None,student_dcid=None):"
if "def fetch_assignments_for_sections" not in cb:
    if marker not in cb:
        raise SystemExit("fetch_assignments marker missing")
    batch_fn = r'''
def fetch_assignments_for_sections(section_ids, student_id, student_dcid=None, debug_tag='batch'):
    """One /assignment/lookup POST for many section IDs."""
    ids=[]
    seen=set()
    for s in section_ids or []:
        if s is None: continue
        s=str(s).strip()
        if not s or s in seen: continue
        seen.add(s); ids.append(s)
    if not ids:
        return {'by_section':{}, 'assignments':[], 'count':0}
    if not student_dcid:
        debug('WARNING: batch section lookup has no resolved student DCID; refusing portal student_id=%s' % student_id)
        return {'by_section':{}, 'assignments':[], 'count':0, 'error':'No PowerSchool student DCID resolved for batch section lookup'}
    start,end=current_school_year_dates()
    ctx={
        'section_ids':ids,
        'start_date':start,
        'end_date':end,
        'studentdcid':str(student_dcid),
    }
    url=BASE_URL+'/ws/xte/assignment/lookup'
    payload=lookup_payload(ctx,student_id)
    debug('Batch section lookup: %d section(s) dcid=%s' % (len(ids), student_dcid))
    debug('Assignment URL: '+url)
    debug('Assignment payload: '+json.dumps(payload))
    rr=post_json(url,payload,{'Referer':HOME_URL,'Origin':BASE_URL,'X-Requested-With':'XMLHttpRequest'})
    if DEBUG:
        safe=re.sub(r'[^A-Za-z0-9_-]+','_',debug_tag).strip('_') or 'batch'
        save_debug('powerschool_assignment_response_%s_batch.txt'%safe,rr['body'])
    if rr['status']>=400:
        debug('Batch assignment HTTP %s response: %s'%(rr['status'],norm(rr['body'])[:1000]))
        return {'by_section':{}, 'assignments':[], 'count':0, 'error':'Assignment lookup HTTP %s'%rr['status'], 'response_status':rr['status']}
    parsed=parse_assignments(rr['body'])
    flat=parsed.get('assignments') or []
    by_section={}
    for a in flat:
        key=str(a.get('section_dcid') or '')
        if not key:
            continue
        bucket=by_section.setdefault(key, {'assignments':[], 'count':0, 'section_id':key})
        bucket['assignments'].append(a)
        bucket['count']=len(bucket['assignments'])
    for sid in ids:
        by_section.setdefault(sid, {'assignments':[], 'count':0, 'section_id':sid})
    debug('Batch assignment lookup: %d assignment(s) across %d section bucket(s)' % (len(flat), len(by_section)))
    return {
        'by_section': by_section,
        'assignments': flat,
        'count': len(flat),
        'response_status': rr['status'],
        'response_bytes': len(rr.get('body','')),
        'student_dcid': str(student_dcid),
    }

'''
    cb = cb.replace(marker, batch_fn + marker, 1)

old_loop_start = "    for c in courses:\n        cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','grade_level','grade_scale','term_grades','section_id','absences','tardies','teacher','room')}"
if old_loop_start not in cb:
    if "batch_section_lookup" in cb:
        print("batch loop already applied")
        compile(cb, str(p), "exec")
        p.write_text(cb, encoding="utf-8")
        raise SystemExit(0)
    raise SystemExit("course loop start not found")

end_marker = "        result['courses'].append(cr)\n    try:\n        roster=[]"
if end_marker not in cb:
    raise SystemExit("course loop end not found")

i0 = cb.find(old_loop_start)
i1 = cb.find(end_marker, i0)
i1_end = i1 + len("        result['courses'].append(cr)\n")

new_loop = r'''    # Phase 1: build course shells + discover section ids without assignment HTTP
    pending=[]
    for c in courses:
        cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','grade_level','grade_scale','term_grades','section_id','absences','tardies','teacher','room')}
        cr['assignments']=[]
        cr['is_current_term']=True
        cr['term_label']='Current'
        link=score_link(c)
        if not cr.get('section_id'):
            discovered=discover_section_id_from_source(src,c.get('course',''))
            if discovered:
                cr['section_id']=discovered
                cr['section_id_source']='home_page_discovery'
        if DEBUG and not link:
            debug_course_discovery(c,src)
        pending.append((c, cr, link))

    # Phase 2: one multi-section assignment lookup when DCID + section ids known
    by_section={}
    if GET_ASSIGNMENTS and student_dcid:
        batch_ids=[]
        for _c, cr, _link in pending:
            if cr.get('section_id'):
                batch_ids.append(str(cr['section_id']))
        if batch_ids:
            batch=fetch_assignments_for_sections(
                batch_ids, sid, student_dcid=student_dcid,
                debug_tag='%s_batch'%re.sub(r'[^A-Za-z0-9_-]+','_',name),
            )
            by_section=batch.get('by_section') or {}
            if batch.get('error'):
                debug('Batch assignment lookup error for %s: %s'%(name, batch.get('error')))
            else:
                debug('Batch filled %d section bucket(s) for %s'%(len(by_section), name))

    # Phase 3: attach assignments (batch first, fall back per-course)
    for c, cr, link in pending:
        if not GET_ASSIGNMENTS:
            cr['assignment_count']=0
            cr['assignment_status']='disabled'
            result['courses'].append(cr)
            continue
        ar=None
        sec=str(cr.get('section_id') or '')
        if sec and sec in by_section and not by_section[sec].get('error'):
            ar=by_section[sec]
            cr['assignment_discovery']='batch_section_lookup'
        elif not link and cr.get('section_id'):
            cr['assignment_discovery']='direct_section_lookup'
            ar=fetch_assignments_for_section(cr.get('section_id'),sid,'%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),student_dcid=student_dcid)
        elif not link:
            cr['assignment_count']=0
            cr['assignment_status']='no_score_link'
            result['courses'].append(cr)
            continue
        else:
            if sec and sec in by_section:
                ar=by_section[sec]
                cr['assignment_discovery']='batch_section_lookup'
            else:
                ar=fetch_assignments(
                    urljoin(HOME_URL,link['href']),
                    sid,
                    '%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),
                    section_id=cr.get('section_id'),
                    student_dcid=student_dcid,
                )
        if not ar:
            ar={'assignments':[], 'count':0}
        if ar.get('student_dcid'):
            student_dcid=str(ar['student_dcid'])
            result['student_dcid']=student_dcid
            if ar.get('student_frn'):
                result['student_frn']=ar['student_frn']
            result['identity_source']=result.get('identity_source') or 'score_page'
            debug('Updated student DCID from score page: %s' % student_dcid)
        cr['assignments']=ar.get('assignments',[])
        cr['assignment_count']=ar.get('count',len(cr['assignments']))
        if ar.get('section_id'):
            cr['section_id']=ar['section_id']
            if link and cr.get('assignment_discovery')!='batch_section_lookup':
                cr['section_id_source']='score_page'
        cr['is_current_term']=True
        if link:
            try:
                from urllib.parse import urlparse as _up, parse_qs as _pq
                _q={k:(v[0] if v else None) for k,v in _pq(_up(link.get('href','')).query).items()}
                cr['store_code']=_q.get('fg') or _q.get('store_code') or _q.get('storecode') or cr.get('store_code')
                cr['term_id']=_q.get('termid') or _q.get('term_id') or cr.get('term_id')
            except Exception:
                pass
        if ar.get('start_date'): cr['term_start']=ar.get('start_date')
        if ar.get('end_date'): cr['term_end']=ar.get('end_date')
        if ar.get('store_code') and not cr.get('store_code'): cr['store_code']=ar.get('store_code')
        if ar.get('term_id') and not cr.get('term_id'): cr['term_id']=ar.get('term_id')
        sc=str(cr.get('store_code') or '').strip()
        if sc:
            cr['term_label']=sc.upper()
        elif cr.get('term_id'):
            cr['term_label']='Term %s'%cr.get('term_id')
        else:
            cr['term_label']='Current'
        if ar.get('error'):
            cr['assignment_error']=ar['error']
            cr['assignment_status']='error'
        elif cr['assignment_count']:
            cr['assignment_status']='ok'
        else:
            cr['assignment_status']='no_assignments'
        result['courses'].append(cr)
'''

cb = cb[:i0] + new_loop + cb[i1_end:]
compile(cb, str(p), "exec")
p.write_text(cb, encoding="utf-8")
print("patched", p)
print("  batch fn:", "def fetch_assignments_for_sections" in cb)
print("  batch discovery:", "batch_section_lookup" in cb)
print("  DELAY 0.05:", "POWERSCHOOL_DELAY','0.05" in cb or 'POWERSCHOOL_DELAY","0.05' in cb)
