"""Per-student course/assignment aggregation."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from .ps_http import (
    DEBUG,
    GET_ASSIGNMENTS,
    HOME_URL,
    candidate_photo_urls,
    debug,
    discover_student_photo,
    frn_dcid,
    get,
    norm,
    save_student_photo,
    switch_student,
    try_save_photo_candidates,
)
from .ps_grades import parse_grade_table
from .ps_assign import (
    debug_course_discovery,
    debug_student_page,
    discover_section_id_from_source,
    discover_student_dcid,
    discover_student_identity,
    fetch_assignments,
    fetch_assignments_for_section,
    score_link,
)

def process_student(st, photo_dir=None):
    sid=st['student_id'];name=st['name'];debug('Switching student %s (%s)'%(sid,name));sw=switch_student(sid)
    if sw['status']>=400:return {'student_id':sid,'name':name,'error':'Student switch HTTP %s'%sw['status'],'courses':[]}
    home=get(HOME_URL);page=home if home['status']<400 else sw;debug_student_page(sid,name,page);src=page['body'];courses=parse_grade_table(src)
    if not courses and page is not sw:courses=parse_grade_table(sw['body'])
    if not courses:debug('No actual ccid course rows found for %s. Student remains valid.'%name)
    identity=discover_student_identity(src)
    if not identity.get('student_dcid'):
        identity=discover_student_identity(sw.get('body',''))
    student_dcid=identity.get('student_dcid')
    student_frn=identity.get('student_frn')

    if not student_frn or identity.get('identity_source') != 'studentfrn':
        for probe_course in courses:
            probe_link=score_link(probe_course)
            if not probe_link:
                continue
            probe=get(urljoin(HOME_URL,probe_link['href']))
            if probe['status']>=400:
                continue
            probe_identity=discover_student_identity(probe.get('body',''))
            if probe_identity.get('student_dcid'):
                identity=probe_identity
                student_dcid=probe_identity.get('student_dcid')
                student_frn=probe_identity.get('student_frn') or student_frn
                debug('Resolved student identity from score page: dcid=%s frn=%s' % (student_dcid,student_frn))
                break

    if not student_dcid:
        debug('WARNING: could not resolve PowerSchool student DCID for %s (portal student_id=%s)'%(name,sid))
    else:
        debug('Resolved student DCID: %s (portal student_id=%s)'%(student_dcid,sid))
    result={'student_id':sid,'student_dcid':student_dcid,'student_frn':student_frn,
            'identity_source':identity.get('identity_source'),'name':name,'courses':[]}
    photo_url=st.get('photo_source_url') or discover_student_photo(src,sid) or discover_student_photo(sw.get('body',''),sid)
    local_photo=None
    if photo_url:
        result['photo_source_url']=photo_url
        local_photo=save_student_photo(photo_url,sid,photo_dir)
    if not local_photo and photo_dir:
        candidates=candidate_photo_urls(sid, student_frn=student_frn, student_dcid=student_dcid)
        src_url, local_photo = try_save_photo_candidates(candidates, sid, photo_dir)
        if src_url:
            result['photo_source_url']=src_url
    if local_photo:
        result['photo_url']=local_photo
    else:
        debug('No student photo found for %s (id=%s frn=%s dcid=%s)'%(name,sid,student_frn,student_dcid))
    if not courses:
        debug('No course rows/links found for %s. Student remains valid.'%name);return result
    for c in courses:
        cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','section_id')}
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
        if not GET_ASSIGNMENTS:
            cr['assignment_count']=0
            cr['assignment_status']='disabled'
            result['courses'].append(cr)
            continue
        if not link and cr.get('section_id'):
            ar=fetch_assignments_for_section(cr['section_id'],sid,debug_tag='%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),student_dcid=student_dcid)
        elif link:
            ar=fetch_assignments(urljoin(HOME_URL,link['href']),sid,'%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),section_id=cr.get('section_id'),student_dcid=student_dcid)
        else:
            cr['assignment_count']=0
            cr['assignment_status']='no_score_link'
            result['courses'].append(cr)
            continue
        if ar.get('student_dcid'):
            student_dcid=str(ar['student_dcid'])
            result['student_dcid']=student_dcid
            if ar.get('student_frn'):
                result['student_frn']=ar['student_frn']
            result['identity_source']=result.get('identity_source') or 'score_page'
        cr['assignments']=ar.get('assignments',[])
        cr['assignment_count']=ar.get('count',len(cr['assignments']))
        if ar.get('section_id'):
            cr['section_id']=ar['section_id']
            if link:
                cr['section_id_source']='score_page'
        cr['is_current_term']=True
        if link:
            try:
                _q={k:(v[0] if v else None) for k,v in parse_qs(urlparse(link.get('href','')).query).items()}
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
    return result
