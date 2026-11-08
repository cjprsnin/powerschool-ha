#!/usr/bin/env python3
import argparse, getpass, html, json, os, re, sys, time
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError, URLError

BASE_URL=os.environ.get('POWERSCHOOL_URL','').rstrip('/')
PUBLIC_URL=BASE_URL+'/public/'
LOGIN_URL=BASE_URL+'/guardian/home.html'
HOME_URL=LOGIN_URL
LOOKUP_URL=os.environ.get('POWERSCHOOL_ASSIGNMENT_LOOKUP_URL','').strip()
TIMEOUT=int(os.environ.get('POWERSCHOOL_TIMEOUT','30'))
DELAY=float(os.environ.get('POWERSCHOOL_DELAY','.25'))
DEBUG=os.environ.get('POWERSCHOOL_DEBUG','').lower() in ('1','true','yes','on')
GET_ASSIGNMENTS=os.environ.get('POWERSCHOOL_GET_ASSIGNMENTS','1').lower() not in ('0','false','no','off')
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0 Safari/537.36'
jar=CookieJar(); opener=None

def debug(s):
    if DEBUG: print('[DEBUG] '+str(s),file=sys.stderr)
def save_debug(name,text):
    if DEBUG:
        try:
            with open(name,'w',encoding='utf-8') as f:f.write(text or '')
            debug('Saved '+name)
        except Exception as e:debug('Could not save %s: %s'%(name,e))
def norm(x):return re.sub(r'\s+',' ',html.unescape(str(x or ''))).strip()
def strip(x):return norm(re.sub(r'<[^>]+>',' ',str(x or '')))
def clean_course_name(text):
    """Extract the actual course name from PowerSchool's Course cell.

    The attendance/grade table commonly renders cells like:
    "Science 7 Email Genco, Rebecca - Rm: 154".
    We want only "Science 7" and not the teacher/room metadata.
    """
    text=norm(text)
    if not text:
        return ''
    text=re.split(r'\s+Email\s+',text,maxsplit=1,flags=re.I)[0]
    text=re.sub(r'\s+-\s+Rm:\s*[^\s]+.*$','',text,flags=re.I)
    return norm(text)

def num(x):
    try:return float(str(x).replace('%','').strip())
    except Exception:return None
def intval(x):
    m=re.search(r'\d+',str(x or ''));return int(m.group()) if m else None
def first(d,*keys):
    if not isinstance(d,dict):return None
    low={str(k).lower():v for k,v in d.items()}
    for k in keys:
        v=low.get(k.lower())
        if v not in (None,''):return v
    return None

def _ensure_opener():
    global jar, opener
    if opener is None:
        jar=CookieJar()
        opener=build_opener(HTTPCookieProcessor(jar))
    return opener

def request(url,method='GET',data=None,json_data=None,headers=None):
    global opener
    _ensure_opener()
    h={'User-Agent':UA,'Accept':'*/*'};h.update(headers or {});body=None
    if json_data is not None:
        body=json.dumps(json_data).encode();h.setdefault('Content-Type','application/json');h.setdefault('Accept','application/json, text/plain, */*')
    elif data is not None:
        body=urlencode(data).encode();h.setdefault('Content-Type','application/x-www-form-urlencoded')
    req=Request(url,data=body,headers=h,method=method);time.sleep(DELAY);debug('%s %s'%(method,url))
    try:
        r=opener.open(req,timeout=TIMEOUT);raw=r.read();enc=r.headers.get_content_charset() or 'utf-8';text=raw.decode(enc,errors='replace');debug('HTTP %s %s (%d bytes)'%(r.status,r.geturl(),len(raw)))
        return {'status':r.status,'url':r.geturl(),'headers':r.headers,'body':text}
    except HTTPError as e:
        raw=e.read();text=raw.decode(e.headers.get_content_charset() or 'utf-8',errors='replace');return {'status':e.code,'url':e.geturl(),'headers':e.headers,'body':text,'error':str(e)}
    except URLError as e:return {'status':0,'url':url,'headers':{},'body':'','error':str(e)}
def get(url,headers=None):return request(url,'GET',headers=headers)
def post(url,data,headers=None):return request(url,'POST',data=data,headers=headers)
def post_json(url,data,headers=None):return request(url,'POST',json_data=data,headers=headers)

def login(user,pw):
    get(PUBLIC_URL)
    payload={'account':user,'pw':pw,'dbpw':'','ldappassword':'','translator':'','translatorPassword':'','returnUrl':'','serviceName':'','serviceTicket':'','pcasServerUrl':'','credentialType':'','request_locale':'en_US'}
    r=post(LOGIN_URL,payload,{'Referer':PUBLIC_URL,'Origin':BASE_URL});debug('Login status=%s final=%s'%(r['status'],r['url']));save_debug('powerschool_debug_login.html',r['body']);return r

def login_success(r):
    s=r['body'].lower();good=('switchstudent','studentfrn','studentdcid','attbyclass','logout','studentscores','student scores');return any(x in s for x in good)

def frn_dcid(v):
    """Convert PowerSchool's student FRN into the DCID used by XTE.

    Most PowerSchool installations expose a value such as ``00117088``.
    The ``001`` prefix is a district/database prefix, while the remaining
    digits are the student DCID.  If a page already gives us a plain numeric
    DCID, keep it unchanged.
    """
    text=html.unescape(str(v or '')).strip()
    m=re.fullmatch(r'0*001(\d+)',text)
    if m:
        return m.group(1)
    # Some installations expose a numeric FRN without the 001 prefix.
    if text.isdigit():
        return text.lstrip('0') or '0'
    return None

def extract_photo_source(fragment):
    """Find the actual student-photo source used by the authenticated portal.

    PowerSchool builds vary, so do not assume a fixed /photos/... URL. Look for
    normal img attributes first, then CSS background-image URLs.
    """
    if not fragment:
        return None
    patterns = [
        r'<img\b[^>]*(?:src|data-src|data-original|data-image|data-photo)\s*=\s*["\']([^"\']+)["\']',
        r'<img\b[^>]*\b(?:src|data-src|data-original|data-image|data-photo)\s*=\s*([^\s>]+)',
        r'background-image\s*:\s*url\(\s*["\']?([^"\')]+)',
    ]
    for pat in patterns:
        m=re.search(pat,fragment,re.I|re.S)
        if m:
            value=html.unescape(m.group(1)).strip()
            if value and not value.lower().startswith(('data:image/svg','javascript:')):
                return value
    return None

def find_students(src):
    students={}
    pattern=re.compile(r'<a\b[^>]*href\s*=\s*["\']javascript:\s*switchStudent\(\s*(\d+)\s*\)\s*;?\s*["\'][^>]*>\s*(.*?)\s*</a>',re.I|re.S)
    for match in pattern.finditer(src):
        student_id=match.group(1);fragment=match.group(2)
        name=re.sub(r'<[^>]+>',' ',fragment);name=html.unescape(name);name=re.sub(r'\s+',' ',name).strip() or 'Student '+student_id
        photo=extract_photo_source(fragment)
        students[student_id]={'student_id':student_id,'name':name}
        if photo:
            students[student_id]['photo_source_url']=urljoin(HOME_URL,photo)
        debug('Student switch entry: %s -> %s%s'%(student_id,name,(' photo='+students[student_id]['photo_source_url']) if photo else ''))
    debug('Student discovery found %d candidates'%len(students));return list(students.values())

def discover_student_photo(src, student_id):
    """Find the photo associated with one student on an authenticated page."""
    if not src or not student_id:
        return None
    pat=re.compile(r'<a\b[^>]*href\s*=\s*["\']javascript:\s*switchStudent\(\s*'+re.escape(str(student_id))+r'\s*\)\s*;?\s*["\'][^>]*>(.*?)</a>',re.I|re.S)
    m=pat.search(src)
    if m:
        photo=extract_photo_source(m.group(1))
        if photo:
            return urljoin(HOME_URL,photo)
    return None


def candidate_photo_urls(student_id, student_frn=None, student_dcid=None):
    """Build common PowerSchool student-photo endpoint candidates."""
    urls = []
    seen = set()
    def add(u):
        if u and u not in seen:
            seen.add(u); urls.append(u)
    base = HOME_URL.rstrip('/')
    # FRN forms (001 + dcid is common)
    frns = []
    if student_frn:
        frns.append(str(student_frn))
        if str(student_frn).isdigit() and not str(student_frn).startswith('001'):
            frns.append('001' + str(student_frn).lstrip('0'))
    if student_dcid and not student_frn:
        frns.append('001' + str(student_dcid).lstrip('0'))
        frns.append(str(student_dcid))
    ids = []
    for v in (student_id, student_dcid, student_frn):
        if v is not None and str(v).strip():
            ids.append(str(v).strip())
    for frn in frns:
        add('%s/guardian/studentphoto?photo_type=student&studentfrn=%s' % (base, frn))
        add('%s/guardian/studentphoto?studentfrn=%s' % (base, frn))
    for sid in ids:
        add('%s/guardian/studentphoto?photo_type=student&student_id=%s' % (base, sid))
        add('%s/guardian/studentphoto?student_id=%s' % (base, sid))
        add('%s/guardian/studentphoto?id=%s' % (base, sid))
        add('%s/photos/%s.jpg' % (base, sid))
        add('%s/photos/%s.png' % (base, sid))
    return urls

def try_save_photo_candidates(candidates, student_id, photo_dir):
    """Try each candidate URL until one downloads as an image."""
    for url in candidates or []:
        local = save_student_photo(url, student_id, photo_dir)
        if local:
            debug('Student photo saved from %s -> %s' % (url, local))
            return url, local
    return None, None

def save_student_photo(photo_url, student_id, photo_dir):
    """Download an authenticated student photo into a local web directory."""
    if not photo_url or not photo_dir:
        return None
    try:
        req=Request(photo_url,headers={'User-Agent':UA,'Accept':'image/avif,image/webp,image/apng,image/*,*/*;q=0.8','Referer':HOME_URL})
        rr=opener.open(req,timeout=TIMEOUT)
        raw=rr.read(); ctype=rr.headers.get('Content-Type','')
        if not raw:
            return None
        if ctype and not ctype.lower().startswith('image/'):
            if not (raw.startswith(b'\xff\xd8\xff') or raw.startswith(b'\x89PNG') or raw.startswith(b'GIF8') or raw.startswith(b'RIFF')):
                debug('Student photo response was not an image: %s'%ctype);return None
        ext='.jpg'
        lc=ctype.lower()
        if 'png' in lc or raw.startswith(b'\x89PNG'): ext='.png'
        elif 'webp' in lc or raw.startswith(b'RIFF'): ext='.webp'
        elif 'gif' in lc or raw.startswith(b'GIF8'): ext='.gif'
        os.makedirs(photo_dir,exist_ok=True)
        for old in ('.jpg','.jpeg','.png','.webp','.gif'):
            try: os.remove(os.path.join(photo_dir,str(student_id)+old))
            except FileNotFoundError: pass
        path=os.path.join(photo_dir,str(student_id)+ext)
        tmp=path+'.tmp'
        with open(tmp,'wb') as f:f.write(raw)
        os.replace(tmp,path)
        return '/local/powerschool/'+str(student_id)+ext
    except Exception as e:
        debug('Student photo download failed: %s'%e)
        return None

def switch_student(i):return post(LOGIN_URL,{'selected_student_id':str(i)},{'Referer':HOME_URL,'Origin':BASE_URL})
def attrs(tag):return {m.group(1).lower():m.group(3) for m in re.finditer(r'([\w:-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S)}
def cells(row):
    out=[]
    for m in re.finditer(r'<(td|th)\b([^>]*)>(.*?)</\1>',row,re.I|re.S):
        a=attrs(m.group(2));c={'text':strip(m.group(3)),'html':m.group(3),'attrs':a};n=intval(a.get('colspan')) or 1;out += [c]*max(1,n)
    return out

class PowerSchoolGradeTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]
        self.in_row=False
        self.current_row=None
        self.in_cell=False
        self.current_cell=None
        self.cell_depth=0
        self.current_link=None
        self.link_depth=0
        self.text_parts=[]

    def handle_starttag(self, tag, attrs):
        tag=tag.lower(); a={k.lower():v for k,v in attrs}
        if tag=='tr':
            if self.in_row:
                self.handle_endtag('tr')
            rid=a.get('id','') or ''
            self.in_row=True
            self.current_row={'attrs':a,'cells':[],'links':[],'id':rid}
            self.current_cell=None
            self.current_link=None
            self.cell_depth=0
            self.link_depth=0
        if self.in_row:
            sid=(a.get('data-sectionid') or a.get('data-section-id') or a.get('data-section_id'))
            if sid and re.fullmatch(r'\d+',str(sid)):
                self.current_row['section_id']=str(sid)
            # Some PowerSchool builds expose the section as a plain sectionId attribute.
            for key in ('sectionid','section-id','section_id','sectionid'):
                val=a.get(key)
                if val and re.fullmatch(r'\d+',str(val)) and not self.current_row.get('section_id'):
                    self.current_row['section_id']=str(val)

        if tag=='tr':
            pass
        elif self.in_row and tag in ('td','th') and self.current_cell is None:
            self.in_cell=True
            self.current_cell={'attrs':a,'text':'','html':'','links':[],'tag':tag}
            self.cell_depth=1
            self.text_parts=[]
        elif self.in_cell:
            self.cell_depth += 1
            if tag=='a':
                self.current_link={'href':a.get('href','') or '', 'text':'','attrs':a}
                self.link_depth=1
            elif self.current_link is not None:
                self.link_depth += 1

    def handle_endtag(self, tag):
        tag=tag.lower()
        if self.in_cell and tag=='a' and self.current_link is not None and self.link_depth==1:
            self.current_link['text']=norm(self.current_link.get('text',''))
            self.current_cell['links'].append(self.current_link)
            self.current_row['links'].append(self.current_link)
            self.current_link=None
            self.link_depth=0
            return
        if self.in_cell and self.current_link is not None and self.link_depth>0:
            self.link_depth -= 1
        if self.in_cell and tag in ('td','th'):
            self.current_cell['text']=norm(''.join(self.text_parts))
            self.current_cell['html']=''
            self.current_row['cells'].append(self.current_cell)
            self.current_cell=None
            self.in_cell=False
            self.cell_depth=0
            self.text_parts=[]
            return
        if self.in_row and tag=='tr':
            rid=self.current_row.get('attrs',{}).get('id','')
            if re.match(r'^ccid_\d+$',rid,re.I):
                self.rows.append(self.current_row)
            self.in_row=False
            self.current_row=None
            self.current_cell=None
            self.current_link=None
            self.cell_depth=0
            self.link_depth=0

    def handle_data(self, data):
        if not self.in_cell:
            return
        if self.current_link is not None:
            self.current_link['text'] = self.current_link.get('text','') + data
        self.text_parts.append(data)

def grade_value(t):
    t=norm(t)
    if not t:return {}
    m=re.fullmatch(r'([A-F][+-]?)(\d{1,3})',t,re.I)
    if m:
        letter=m.group(1).upper();pct=float(m.group(2))
        return {'raw':t,'earned':None,'possible':None,'percent':pct,'letter':letter}
    m=re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)',t)
    if m:
        e,p=float(m.group(1)),float(m.group(2));return {'raw':t,'earned':e,'possible':p,'percent':round(e/p*100,2) if p else None,'letter':None}
    m=re.search(r'(\d+(?:\.\d+)?)\s*%',t)
    if m:return {'raw':t,'percent':float(m.group(1)),'letter':None}
    m=re.fullmatch(r'([A-F][+-]?)',t,re.I)
    if m:return {'raw':t,'percent':None,'letter':m.group(1).upper()}
    return {'raw':t,'percent':None,'letter':None}

def parse_grade_table(src):
    parser=PowerSchoolGradeTableParser()
    parser.feed(src)
    rows=parser.rows
    debug('HTMLParser found %d ccid course rows' % len(rows))
    if not rows:
        return []

    def _header_label(attrs_str, cell_inner):
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

    output=[]
    for i,row in enumerate(rows):
        row_id=row['attrs'].get('id','')
        values=[norm(c['text']) for c in row['cells']]
        links=[]
        for link in row.get('links',[]):
            href=link.get('href','')
            # The hrefs in this table are relative to /guardian/home.html.
            absolute=urljoin(HOME_URL,href)
            item=dict(link);item['href']=absolute
            links.append(item)

        # PowerSchool's actual Course cell uses class=table-element-text-align-start.
        # This avoids mistaking period/grade cells such as '0(A)' for the course.
        course=''
        course_index=None
        for j,cell in enumerate(row['cells']):
            cls=str(cell.get('attrs',{}).get('class','') or '')
            if 'table-element-text-align-start' in cls:
                candidate=clean_course_name(cell.get('text',''))
                if candidate:
                    course=candidate;course_index=j;break

        # Fallback: identify the cell containing teacher Email metadata.
        if not course:
            for j,cell in enumerate(row['cells']):
                txt=norm(cell.get('text',''))
                if re.search(r'\bEmail\b',txt,re.I):
                    candidate=clean_course_name(txt)
                    if candidate:
                        course=candidate;course_index=j;break

        # Fallback: identify a cell whose HTML contains a scores/teacher link
        # and use the visible text before the teacher details.
        if not course:
            for j,cell in enumerate(row['cells']):
                txt=norm(cell.get('text',''))
                if txt and not re.fullmatch(r'(?:Not available|\[ i \]|[A-F][+-]?\d{0,3})',txt,re.I):
                    if 'Email' in txt or re.search(r'\bRm:\s*',txt,re.I):
                        candidate=clean_course_name(txt)
                        if candidate:
                            course=candidate;course_index=j;break

        if not course:
            debug('Skipping ccid row %s: could not identify Course cell' % row_id)
            continue

        # A grade is represented by the text of the first scores.html link
        # that is not an informational [ i ] placeholder. Prefer a link with
        # a begin/end date or the current-term fg value.
        score_links=[x for x in links if 'scores.html' in x.get('href','').lower()]
        grade_raw=''
        grade_link=None
        for link in score_links:
            label=norm(link.get('text',''))
            if label and label != '[ i ]':
                grade_raw=label;grade_link=link;break
        if grade_link is None and score_links:
            # Keep a usable score page even when there is no grade yet.
            grade_link=score_links[0]

        # Also support a grade rendered in a non-link cell.
        if not grade_raw:
            for value in values:
                if re.fullmatch(r'[A-F][+-]?\d{1,3}',value,re.I) or re.fullmatch(r'[A-F][+-]?',value,re.I):
                    grade_raw=value;break
                if re.fullmatch(r'\d+(?:\.\d+)?%',value) or re.fullmatch(r'\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?',value):
                    grade_raw=value;break

        # Current PowerSchool score pages expose the course section as
        # data-sectionid=\"...\" on elements inside the ccid row.
        section_id=row.get('section_id')
        if not section_id:
            section_id=discover_section_id_from_source(src,course)
        if not section_id:
            for link in links:
                href=link.get('href','')
                m=re.search(r'[?&]sectionId=(\d+)',href,re.I)
                if m:
                    section_id=m.group(1);break

        if DEBUG:
            debug('ccid row %d id=%s course=%r grade=%r score_links=%d' % (i,row_id,course,grade_raw,len(score_links)))

        g=grade_value(grade_raw)

        def _cell_count(idx):
            if idx is None or idx < 0 or idx >= len(values):
                return None
            raw=values[idx]
            if raw in ('', '-', '--', '—', 'N/A', 'n/a'):
                return 0
            n=intval(raw)
            return n if n is not None else None

        use_abs, use_tardy, use_att = abs_idx, tardy_idx, att_idx
        nvals=len(values)
        # Guardian tables always put Absences/Tardies as the last two data cells.
        tail = [norm(h).lower() for h in (header_values[-2:] if header_values else [])]
        headers_end_with_att = (
            len(tail) == 2
            and any(h.startswith('absence') or h == 'abs' for h in tail)
            and any(h.startswith('tard') or h == 'tdy' for h in tail)
        )
        if headers_end_with_att and nvals >= 2:
            use_abs, use_tardy = nvals - 2, nvals - 1
        elif (use_abs is not None and use_abs >= nvals) or (use_tardy is not None and use_tardy >= nvals):
            if nvals >= 2 and abs_idx is not None and tardy_idx is not None:
                use_abs, use_tardy = nvals - 2, nvals - 1
            elif nvals >= 1 and abs_idx is not None:
                use_abs = nvals - 1
        absences=_cell_count(use_abs)
        tardies=_cell_count(use_tardy)
        if absences is None and use_att is not None and abs_idx is None:
            absences=_cell_count(use_att if use_att < nvals else (nvals - 1 if nvals else None))
        if DEBUG and i < 3:
            debug('att cells row=%s nvals=%s use_abs=%s use_tardy=%s abs=%s tardy=%s tail=%s values_tail=%s' % (
                row_id, nvals, use_abs, use_tardy, absences, tardies, tail, values[-4:] if values else []))

        output.append({
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
        })

    debug('Parsed %d actual ccid course rows' % len(output))
    parse_grade_table.last_headers = list(header_values)
    parse_grade_table.last_abs_idx = abs_idx
    parse_grade_table.last_tardy_idx = tardy_idx
    return output



def current_school_year_range():
    """Return the current school-year window without district-specific dates.

    PowerSchool installations vary in their term calendars. We prefer dates
    discovered from the authenticated scores page. When a direct section
    lookup has no page-derived dates, use a broad July 1 -> June 30 school
    year window so the integration never needs a hard-coded calendar year.
    """
    now = time.localtime()
    if now.tm_mon >= 7:
        start_year = now.tm_year
    else:
        start_year = now.tm_year - 1
    return f"{start_year}-7-1", f"{start_year + 1}-6-30"

def current_school_year_dates():
    start, end = current_school_year_range()
    return normalize_ps_date(start), normalize_ps_date(end)

def normalize_ps_date(value):
    """Normalize PowerSchool dates to the format accepted by /assignment/lookup.

    The XTE assignment service expects ISO-like dates such as 2026-8-13,
    not the MM/DD/YYYY values used by some scores.html URLs.
    """
    if not value:
        return None
    value=html.unescape(str(value)).strip()
    m=re.fullmatch(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',value)
    if m:
        return f"{int(m.group(1))}-{int(m.group(2))}-{int(m.group(3))}"
    m=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})',value)
    if m:
        return f"{int(m.group(3))}-{int(m.group(1))}-{int(m.group(2))}"
    return None

def extract_date_from_source(src, names):
    """Find a date value from common PowerSchool/Angular variable names."""
    for name in names:
        patterns=[
            rf'[\"\']{re.escape(name)}[\"\']\s*[:=]\s*[\"\']([^\"\']+)',
            rf'\b{re.escape(name)}\b\s*[:=]\s*[\"\']([^\"\']+)',
            rf'\b{re.escape(name)}\b\s*=\s*new\s+Date\s*\(\s*[\"\']([^\"\']+)'
        ]
        for pat in patterns:
            m=re.search(pat,src,re.I|re.S)
            if m:
                v=normalize_ps_date(m.group(1))
                if v:return v
    return None

def context(src,url):
    q={k:v[0] for k,v in parse_qs(urlparse(url).query).items()}
    # scores.html carries some values in JS/Angular config, sometimes as
    # JSON-style quoted keys and sometimes as plain assignments.
    def rx(pattern):
        m=re.search(pattern,src,re.I|re.S)
        return html.unescape(m.group(1)).strip() if m else None

    for k,p in [
        ('studentfrn',r'(?:[\"\']student[_-]?frn[\"\']?|\bstudent[_-]?frn\b)\s*[:=]\s*[\"\']([^\"\']+)'),
        ('studentdcid',r'(?:[\"\']student[_-]?dcid[\"\']?|\bstudent[_-]?dcid\b)\s*[:=]\s*[\"\']?(\d+)'),
        ('start_date',r'(?:[\"\']start_date[\"\']?|\bstart_date\b)\s*[:=]\s*[\"\']([^\"\']+)'),
        ('end_date',r'(?:[\"\']end_date[\"\']?|\bend_date\b)\s*[:=]\s*[\"\']([^\"\']+)'),
        ('term_id',r'(?:[\"\']term[_-]?id[\"\']?|\bterm[_-]?id\b)\s*[:=]\s*[\"\']?(\d+)'),
        ('store_code',r'(?:[\"\']store[_-]?code(?:s)?[\"\']?|\bstore[_-]?code(?:s)?\b)\s*[:=]\s*[\"\']([^\"\']+)')]:
        v=rx(p)
        if v:q[k]=v

    # A score page may contain `start_date: beginningDate` / `end_date: endingDate`.
    # Those are JavaScript variable references, not dates. Reject them before
    # building the assignment request so the API never receives a date name.
    q['start_date']=normalize_ps_date(q.get('start_date')) if q.get('start_date') else None
    q['end_date']=normalize_ps_date(q.get('end_date')) if q.get('end_date') else None

    # Score URLs can point at a future grading period (for example a T2
    # link with begdate=11/07/2026). That range is valid for the link but not
    # for the currently published assignments. Only use URL dates when the
    # range is current/past; otherwise fall back to the active term window.
    url_start=normalize_ps_date(q.get('begdate')) if q.get('begdate') else None
    url_end=normalize_ps_date(q.get('enddate')) if q.get('enddate') else None
    q['url_start_date']=url_start
    q['url_end_date']=url_end
    if not q.get('start_date') and url_start:
        q['start_date']=url_start
    if not q.get('end_date') and url_end:
        q['end_date']=url_end

    # Most scores.html links omit the dates because PowerSchool supplies the
    # active term window in the page/Javascript instead. Try the common names.
    if not q.get('start_date'):
        q['start_date']=extract_date_from_source(src, [
            'start_date','startDate','termStartDate','term_start_date',
            'begdate','beginDate','begin_date','startDateString'
        ])
    if not q.get('end_date'):
        q['end_date']=extract_date_from_source(src, [
            'end_date','endDate','termEndDate','term_end_date',
            'enddate','endDateString'
        ])

    # If the URL points to a future term, do not query that future range.
    # Use the active/current term instead. This fixes courses whose home-page
    # score link already points at the next term while assignments are still
    # being published in the current term.
    today=time.strftime('%Y-%m-%d')
    if q.get('url_start_date') and q.get('url_start_date') > today:
        q['start_date']=None
        q['end_date']=None

    if not q.get('start_date') or not q.get('end_date'):
        q['start_date'],q['end_date']=current_school_year_dates()

    if not q.get('store_code') and q.get('fg'): q['store_code']=q['fg']

    # PowerSchool has used several spellings for the section-id collection.
    q['section_ids']=[]
    patterns=[
        r'(?:[\"\']section_ids[\"\']?|\bsection_ids\b)\s*[:=]\s*\[([^]]*)\]',
        r'(?:[\"\']sectionIds[\']?|\bsectionIds\b)\s*[:=]\s*\[([^]]*)\]',
        r'(?:[\"\']section_id[\']?|\bsection_id\b)\s*[:=]\s*[\"\']?(\d+)',
        r'(?:[\"\']sectionId[\']?|\bsectionId\b)\s*[:=]\s*[\"\']?(\d+)',
        r'(?:[\"\']sectionid[\']?|\bsectionid\b)\s*[:=]\s*[\"\']?(\d+)'
    ]
    for idx,pat in enumerate(patterns):
        for m in re.finditer(pat,src,re.I|re.S):
            vals=re.findall(r'\d+',m.group(1))
            if vals:q['section_ids'].extend(vals)
        if q['section_ids']:break
    q['section_ids']=list(dict.fromkeys(q['section_ids']))

    m=re.search(r'(?:[\"\']student_ids[\"\']?|\bstudent_ids\b)\s*[:=]\s*\[([^]]*)\]',src,re.I|re.S)
    q['student_ids']=re.findall(r'\d+',m.group(1)) if m else q.get('student_ids',[])
    return q

def resource_root(src):
    m=re.search(r'\bresourceRoot\s*(?:=|:)\s*["\']([^"\']+)',src,re.I)
    return (urljoin(BASE_URL+'/',m.group(1).lstrip('/')).rstrip('/') if m else BASE_URL+'/ws/xte')

def lookup_payload(ctx,student_id):
    """Build the same core payload used by PowerSchool's Angular client."""
    # studentfrn is the strongest identity signal: on some PowerSchool
    # builds the page also contains a portal/student-switch ID in a field
    # named studentdcid. Never let that value override the FRN-derived DCID.
    sid=frn_dcid(ctx.get('studentfrn')) or ctx.get('studentdcid') or student_id
    p={'student_ids':[int(sid)] if str(sid).isdigit() else [sid]}
    if ctx.get('section_ids'):
        p['section_ids']=[int(x) for x in ctx['section_ids']]
    if ctx.get('start_date'):
        p['start_date']=normalize_ps_date(ctx['start_date'])
    if ctx.get('end_date'):
        p['end_date']=normalize_ps_date(ctx['end_date'])
    # Match the known frontend request: student_ids + section_ids + date
    # range. Do not add store_codes or guessed term_ids unless the endpoint
    # proves they are required.
    return p

def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def lists(data,names):
    names={x.lower() for x in names}
    for d in walk(data):
        for k,v in d.items():
            if str(k).lower() in names and isinstance(v,list):return v
    return []

def parse_assignments(text):
    """Parse the actual PowerSchool /ws/xte/assignment/lookup response.

    PowerSchool returns assignments as:

      assignment
        |_ _assignmentsections[]
             |_ name, duedate, scoreentrypoints, totalpointvalue, weight
             |_ iscountedinfinalgrade
             |_ _assignmentcategoryassociations[]
             |    |_ _teachercategory.name
             |_ _assignmentscores[]
                  |_ scorepoints, scorepercent, scorelettergrade
                  |_ ismissing, islate, isincomplete, isexempt

    Keep both score_entry_points and possible/totalpointvalue because
    PowerSchool can apply assignment weights. Use PowerSchool's supplied
    scorepercent instead of recalculating it.
    """
    try:
        data=json.loads(text)
    except Exception:
        m=re.search(r'[\[{]',text or '')
        if not m:
            return {'count':0,'assignments':[],'error':'Assignment response was not JSON'}
        try:
            data=json.loads(text[m.start():])
        except Exception as e:
            return {'count':0,'assignments':[],'error':'Assignment response JSON parse error: %s'%e}

    if data is None:
        return {'count':0,'assignments':[]}

    if isinstance(data,list):
        assignment_objects=data
    elif isinstance(data,dict):
        assignment_objects=[]
        for key in ('_assignments','assignments','data','results'):
            value=data.get(key)
            if isinstance(value,list):
                assignment_objects=value
                break
        if not assignment_objects and (
            '_assignmentsections' in data or
            '_assignmentscores' in data or
            data.get('_name')=='assignment'
        ):
            assignment_objects=[data]
    else:
        return {'count':0,'assignments':[]}

    def bool_value(value):
        if isinstance(value,bool):
            return value
        return str(value or '').strip().lower() in ('true','yes','1')

    out=[]
    for assignment in assignment_objects:
        if not isinstance(assignment,dict):
            continue

        sections=assignment.get('_assignmentsections',[])
        if not isinstance(sections,list):
            continue

        assignment_id=assignment.get('assignmentid',assignment.get('_id'))

        for section in sections:
            if not isinstance(section,dict):
                continue

            name=norm(section.get('name'))
            due=norm(section.get('duedate'))
            score_entry_points=num(section.get('scoreentrypoints'))
            total_point_value=num(section.get('totalpointvalue'))
            weight=num(section.get('weight'))
            counted=bool_value(section.get('iscountedinfinalgrade'))
            section_id=section.get('assignmentsectionid',section.get('_id'))
            section_dcid=section.get('sectionsdcid')
            score_type=norm(section.get('scoretype'))

            category=''
            associations=section.get('_assignmentcategoryassociations',[])
            if isinstance(associations,list):
                ordered=sorted(
                    [x for x in associations if isinstance(x,dict)],
                    key=lambda x:not bool(x.get('isprimary'))
                )
                for assoc in ordered:
                    teacher_category=assoc.get('_teachercategory',{})
                    if isinstance(teacher_category,dict):
                        category=norm(teacher_category.get('name'))
                        if category:
                            break

            scores=section.get('_assignmentscores',[])
            if not isinstance(scores,list):
                scores=[]

            # Some assignments can exist without a score record yet.
            if not scores:
                out.append({
                    'assignment_id':assignment_id,
                    'assignment_section_id':section_id,
                    'section_dcid':section_dcid,
                    'name':name,
                    'due':due,
                    'earned':None,
                    'possible':total_point_value,
                    'score_entry_points':score_entry_points,
                    'percent':None,
                    'letter':'',
                    'weight':weight,
                    'category':category,
                    'score_type':score_type,
                    'missing':False,
                    'late':False,
                    'incomplete':False,
                    'exempt':False,
                    'counted_in_final_grade':counted
                })
                continue

            for score in scores:
                if not isinstance(score,dict):
                    continue

                out.append({
                    'assignment_id':assignment_id,
                    'assignment_section_id':section_id,
                    'section_dcid':section_dcid,
                    'name':name,
                    'due':due,
                    'earned':num(score.get('scorepoints')),
                    'possible':total_point_value,
                    'score_entry_points':score_entry_points,
                    'percent':num(score.get('scorepercent')),
                    'letter':norm(score.get('scorelettergrade')),
                    'weight':weight,
                    'category':category,
                    'score_type':score_type,
                    'missing':bool_value(score.get('ismissing')),
                    'late':bool_value(score.get('islate')),
                    'incomplete':bool_value(score.get('isincomplete')),
                    'exempt':bool_value(score.get('isexempt')),
                    'absent':bool_value(score.get('isabsent')),
                    'collected':bool_value(score.get('iscollected')),
                    'counted_in_final_grade':counted,
                    'actual_score_entered':norm(score.get('actualscoreentered')),
                    'score_entry_date':norm(score.get('scoreentrydate')),
                    'when_modified':norm(score.get('whenmodified'))
                })

    return {'count':len(out),'assignments':out}

def discover_section_id_from_source(src, course_name):
    """Try to discover a section ID near a course name in the home page.

    Some PowerSchool builds omit both scores.html and data-sectionid from a
    course row, but still render the section ID elsewhere in the same course
    widget. This is deliberately generic: no course name is hard-coded.
    """
    if not src or not course_name:
        return None
    name=re.escape(norm(course_name))
    # Look in several windows because the course text may be HTML-encoded or
    # separated from its metadata by Angular markup.
    for m in re.finditer(name, src, re.I):
        lo=max(0,m.start()-2500); hi=min(len(src),m.end()+2500)
        window=src[lo:hi]
        patterns=[
            r'data-sectionid\s*=\s*[\"\'](\d+)',
            r'data-section-id\s*=\s*[\"\'](\d+)',
            r'\bsectionid\b\s*[=:]\s*[\"\']?(\d+)',
            r'\bsection_id\b\s*[=:]\s*[\"\']?(\d+)',
            r'\bsectionId\b\s*[=:]\s*[\"\']?(\d+)'
        ]
        for pat in patterns:
            sm=re.search(pat,window,re.I|re.S)
            if sm:
                return sm.group(1)
    return None

def debug_course_discovery(course, src):
    if not DEBUG:return
    debug('DISCOVERY %s: row_id=%s section_id=%s score_links=%d' % (
        course.get('course'),course.get('row_id'),course.get('section_id'),
        len([x for x in course.get('links',[]) if 'scores.html' in x.get('href','').lower()])))
    debug('DISCOVERY %s attrs=%s' % (course.get('course'),json.dumps(course.get('row_attrs',{}),ensure_ascii=False)))
    debug('DISCOVERY %s cell_attrs=%s' % (course.get('course'),json.dumps(course.get('cell_attrs',[]),ensure_ascii=False)))
    debug('DISCOVERY %s links=%s' % (course.get('course'),json.dumps(course.get('links',[]),ensure_ascii=False)))

def score_link(course):
    links=course.get('links',[])
    if not links:return None
    scores=[]
    for x in links:
        href=html.unescape(str(x.get('href','') or ''))
        if 'scores.html' in href.lower():
            scores.append(x)
    if not scores:return None
    # Prefer the link that actually displays the current grade.
    real=[x for x in scores if norm(x.get('text','')) and norm(x.get('text','')) != '[ i ]']
    return real[0] if real else scores[0]

def fetch_assignments_for_section(section_id,student_id,debug_tag='course',student_dcid=None):
    """Query /assignment/lookup directly when a section ID is known but
    PowerSchool did not expose a usable scores.html link."""
    if not section_id:
        return {'count':0,'assignments':[],'error':'No section ID available'}
    if not student_dcid:
        debug('WARNING: direct section lookup has no resolved student DCID; refusing portal student_id=%s' % student_id)
        return {'count':0,'assignments':[],'error':'No PowerSchool student DCID resolved for direct section lookup','section_id':str(section_id)}
    ctx={
        'section_ids':[str(section_id)],
        'start_date':current_school_year_dates()[0],
        'end_date':current_school_year_dates()[1],
        'studentdcid':str(student_dcid)
    }
    url=BASE_URL+'/ws/xte/assignment/lookup'
    payload=lookup_payload(ctx,student_id)
    debug('Direct section discovery: section_id=%s' % section_id)
    debug('Assignment URL: '+url)
    debug('Assignment payload: '+json.dumps(payload))
    rr=post_json(url,payload,{'Referer':HOME_URL,'Origin':BASE_URL,'X-Requested-With':'XMLHttpRequest'})
    if DEBUG:
        safe=re.sub(r'[^A-Za-z0-9_-]+','_',debug_tag).strip('_') or 'course'
        save_debug('powerschool_assignment_response_%s_direct.txt'%safe,rr['body'])
    if rr['status']>=400:
        debug('Direct assignment HTTP %s response: %s'%(rr['status'],norm(rr['body'])[:1000]))
        return {'count':0,'assignments':[],'error':'Assignment lookup HTTP %s'%rr['status'],'section_id':str(section_id)}
    result=parse_assignments(rr['body'])
    result['section_id']=str(section_id)
    result['response_status']=rr['status']
    result['response_bytes']=len(rr.get('body',''))
    if not result.get('assignments') and not result.get('error'):
        debug('Assignment lookup returned HTTP %s with %d bytes but zero parsed assignments for section=%s student_dcid=%s' % (rr['status'], len(rr.get('body','')), section_id, student_dcid))
    return result

def fetch_assignments(score_url,student_id,debug_tag='course',section_id=None,student_dcid=None):
    r=get(score_url)
    if r['status']>=400:return {'count':0,'assignments':[],'error':'Score page HTTP %s'%r['status']}
    src=r['body']
    if DEBUG:
        safe=re.sub(r'[^A-Za-z0-9_-]+','_',debug_tag).strip('_') or 'course'
        save_debug('powerschool_score_%s.html'%safe,src)
    ctx=context(src,r['url'])
    # Prefer the already-resolved student DCID from the student discovery step.
    # This avoids accidentally replacing a known DCID with a misleading
    # studentdcid value emitted by some PowerSchool page variants.
    resolved_student_dcid=str(student_dcid) if student_dcid else (frn_dcid(ctx.get('studentfrn')) or ctx.get('studentdcid'))
    if resolved_student_dcid:
        ctx['studentdcid']=str(resolved_student_dcid)
    # Prefer the section ID parsed from the student's course row. The score
    # page also contains data-sectionid, which is a useful fallback.
    if section_id:
        ctx['section_ids']=[str(section_id)]
    elif not ctx.get('section_ids'):
        m=re.search(r'data-sectionid\s*=\s*[\"\'](\d+)[\"\']',src,re.I)
        if m:
            ctx['section_ids']=[m.group(1)]
    debug('Score context: '+json.dumps(ctx,ensure_ascii=False))
    root=resource_root(src);url=LOOKUP_URL or root+'/assignment/lookup';payload=lookup_payload(ctx,student_id)
    debug('Assignment URL: '+url);debug('Assignment payload: '+json.dumps(payload))
    rr=post_json(url,payload,{'Referer':r['url'],'Origin':BASE_URL,'X-Requested-With':'XMLHttpRequest'})
    if DEBUG:
        safe=re.sub(r'[^A-Za-z0-9_-]+','_',debug_tag).strip('_') or 'course'
        save_debug('powerschool_assignment_response_%s.txt'%safe,rr['body'])
    if rr['status']>=400:
        debug('Assignment HTTP %s response: %s'%(rr['status'],norm(rr['body'])[:1000]))
        return {'count':0,'assignments':[],'error':'Assignment lookup HTTP %s'%rr['status'],'section_id':(ctx.get('section_ids') or [None])[0],'student_dcid':resolved_student_dcid,'student_frn':ctx.get('studentfrn')}
    result=parse_assignments(rr['body'])
    result['response_status']=rr['status']
    result['response_bytes']=len(rr.get('body',''))
    if not result.get('assignments') and not result.get('error'):
        debug('Assignment lookup returned HTTP %s with %d bytes but zero parsed assignments for section=%s student_dcid=%s' % (rr['status'], len(rr.get('body','')), (ctx.get('section_ids') or [None])[0], resolved_student_dcid))
    # Preserve the resolved PowerSchool section ID in the course record.
    # The student course table does not reliably expose data-sectionid on
    # every row, but the score page always gives us the section used for the
    # assignment lookup.
    result['section_id']=(ctx.get('section_ids') or [None])[0]
    result['student_dcid']=resolved_student_dcid
    result['student_frn']=ctx.get('studentfrn')
    return result

def debug_student_page(student_id,student_name,response):
    if not DEBUG:return
    body=response.get('body','');safe_name=re.sub(r'[^A-Za-z0-9_-]+','_',student_name).strip('_') or 'student';debug_file='powerschool_debug_%s_%s.html'%(student_id,safe_name);save_debug(debug_file,body)
    debug('Student page: %s -> %s (%d bytes)'%(student_name,response.get('url',''),len(body)))
    debug('attByClass present: %s'%('attByClass' in body));ccid_rows=len(re.findall(r'id=["\']ccid_',body,re.I));debug('ccid rows found: %d'%ccid_rows)
    for needle in ('studentScores','assignment','section_id','section_ids','student_id','studentfrn','studentdcid'):
        debug('%s present: %s'%(needle,needle.lower() in body.lower()))

def discover_student_identity(src, fallback=None):
    """Discover the student's PowerSchool identity without assuming IDs match.

    The student switch ID shown by the guardian portal is not guaranteed to be
    the DCID required by /ws/xte/assignment/lookup. Prefer studentfrn because
    the score/assignment pages consistently use it to identify the real
    PowerSchool student. Only fall back to an explicit studentdcid field when
    no FRN is present.
    """
    result={'student_frn':None,'student_dcid':None,'identity_source':None}
    if not src:
        if fallback is not None:
            result['student_dcid']=str(fallback)
            result['identity_source']='fallback'
        return result

    frn_patterns=[
        r'(?:["\']student[_-]?frn["\']?|\bstudent[_-]?frn\b)\s*[:=]\s*["\']?([^"\'\s,};]+)',
        r'<(?:input|select|option)[^>]*\b(?:name|id)\s*=\s*["\']student[_-]?frn["\'][^>]*\bvalue\s*=\s*["\']([^"\']+)',
        r'<(?:input|select|option)[^>]*\bvalue\s*=\s*["\']([^"\']+)["\'][^>]*\b(?:name|id)\s*=\s*["\']student[_-]?frn["\']',
    ]
    for pat in frn_patterns:
        m=re.search(pat,src,re.I|re.S)
        if m:
            frn=html.unescape(m.group(1)).strip()
            dcid=frn_dcid(frn)
            if dcid:
                result.update(student_frn=frn,student_dcid=str(dcid),identity_source='studentfrn')
                return result

    dcid_patterns=[
        r'(?:["\']student[_-]?dcid["\']?|\bstudent[_-]?dcid\b)\s*[:=]\s*["\']?(\d+)',
        r'\bdata-studentdcid\s*=\s*["\'](\d+)',
        r'<(?:input|select|option|[^>]+?)\b[^>]*\b(?:name|id)\s*=\s*["\']student[_-]?dcid["\'][^>]*\bvalue\s*=\s*["\'](\d+)["\']',
        r'<(?:input|select|option|[^>]+?)\b[^>]*\bvalue\s*=\s*["\'](\d+)["\'][^>]*\b(?:name|id)\s*=\s*["\']student[_-]?dcid["\']',
    ]
    for pat in dcid_patterns:
        m=re.search(pat,src,re.I|re.S)
        if m:
            result.update(student_dcid=str(m.group(1)),identity_source='studentdcid')
            return result

    if fallback is not None:
        result.update(student_dcid=str(fallback),identity_source='fallback')
    return result


def discover_student_dcid(src, fallback=None):
    """Backward-compatible wrapper returning only the discovered DCID."""
    return discover_student_identity(src, fallback).get('student_dcid')


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
    # Recount codes from unique days only (not every HTML match)
    codes = {}
    for d in uniq:
        codes[d['code']] = codes.get(d['code'], 0) + 1
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

def scrape_portal_extras(home_src=None):
    schedule, schedule_status = [], 'unavailable'
    if home_src:
        rows = parse_schedule(home_src)
        if rows:
            schedule, schedule_status = rows, 'ok'
            debug('schedule from home.html rows=%s' % len(rows))
    if schedule_status != 'ok':
        for path in ('matrixSchedule.html', 'schedule.html', 'studentschedule.html', 'studentSchedule.html', 'weeklySchedule.html', 'studentMatrixSchedule.html'):
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
    if home_src:
        items = parse_bulletin(home_src)
        if items:
            bulletin, bulletin_status = items, 'ok'
            debug('bulletin from home.html items=%s' % len(items))
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

    # If the home/switch page only exposed the portal ID (or a misleading
    # studentdcid field), probe the first real scores.html page. PowerSchool
    # score pages expose studentfrn, which gives us the assignment API DCID.
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
        # Fallback: common PowerSchool studentphoto endpoints using resolved IDs
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
        cr={k:c.get(k) for k in ('course','grade_raw','grade_percent','grade_letter','section_id','absences','tardies')}
        cr['assignments']=[]
        cr['is_current_term']=True
        cr['term_label']='Current'
        link=score_link(c)
        # Try the course page itself before using the legacy compatibility
        # fallback. This keeps course-specific knowledge out of the normal
        # discovery path.
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
            # No scores.html link, but we have a live section ID. Ask the same
            # XTE assignment service directly instead of declaring no_score_link.
            cr['assignment_discovery']='direct_section_lookup'
            ar=fetch_assignments_for_section(cr.get('section_id'),sid,'%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),student_dcid=student_dcid)
        elif not link:
            cr['assignment_count']=0
            cr['assignment_status']='no_score_link'
            result['courses'].append(cr)
            continue
        else:
            ar=fetch_assignments(
                urljoin(HOME_URL,link['href']),
                sid,
                '%s_%s'%(sid,re.sub(r'[^A-Za-z0-9_-]+','_',c.get('course','course'))),
                section_id=cr.get('section_id'),
                student_dcid=student_dcid,
            )
        # Carry the DCID learned from a normal scores.html page forward to later courses without a scores link.
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
            if link:
                cr['section_id_source']='score_page'
        # Term metadata from score link / assignment context
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
        # Label for UI (T1/T2/S1/Q1/etc.)
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
    try:
        extras = scrape_portal_extras(home_src=src)
        result.update(extras)
    except Exception as _ex:
        debug('portal extras failed: %s' % _ex)
        result.setdefault('schedule_status', 'unavailable')
        result.setdefault('attendance_day_status', 'unavailable')
        result.setdefault('bulletin_status', 'unavailable')
    return result

def main():
    global DEBUG,GET_ASSIGNMENTS
    ap=argparse.ArgumentParser(description='PowerSchool grades and assignments exporter')
    ap.add_argument('--student',help='Process only this student by name')
    ap.add_argument('--pretty',action='store_true',help='Pretty-print JSON output (default output is also JSON)')
    ap.add_argument('--debug',action='store_true',help='Save debug HTML/responses and print debug messages')
    ap.add_argument('--no-assignments',action='store_true',help='Skip assignment lookups')
    ap.add_argument('--output',help='Write the full JSON result to this file (stdout is still produced)')
    ap.add_argument('--ha-output',help='Write a compact Home Assistant JSON view to this file')
    ap.add_argument('--ha-only',action='store_true',help='Output only the compact Home Assistant JSON view')
    a=ap.parse_args()
    DEBUG=DEBUG or a.debug
    GET_ASSIGNMENTS=GET_ASSIGNMENTS and not a.no_assignments
    user=os.environ.get('POWERSCHOOL_USERNAME') or input('PowerSchool username: ').strip();pw=os.environ.get('POWERSCHOOL_PASSWORD') or getpass.getpass('PowerSchool password: ');r=login(user,pw)
    if not login_success(r):
        save_debug('powerschool_login_failed.html',r['body']);print(json.dumps({'_meta':{'version':4,'error':'PowerSchool login failed','http_status':r['status'],'final_url':r['url']}},indent=2));return 1
    students=find_students(r['body'])
    if not students:
        save_debug('powerschool_no_students.html',r['body']);print(json.dumps({'_meta':{'version':4,'error':'No students found','http_status':r['status'],'final_url':r['url']}},indent=2));return 1
    if a.student:
        wanted=a.student.strip().lower()
        selected=[st for st in students if st.get('name','').strip().lower()==wanted]
        if not selected:
            selected=[st for st in students if wanted in st.get('name','').strip().lower()]
        if not selected:
            print(json.dumps({'_meta':{'version':4,'error':'Student not found','requested_student':a.student},'available_students':[st.get('name') for st in students]},indent=2,ensure_ascii=False))
            return 1
        students=selected
    out={'_meta':{'version':4,'updated':time.strftime('%Y-%m-%dT%H:%M:%S'),'students':len(students),'get_assignments':GET_ASSIGNMENTS,'schema':'powerschool_grades_v4'}}
    for st in students:
        try:res=process_student(st)
        except Exception as e:debug('Unhandled error processing %s: %s'%(st['name'],e));res={'student_id':st['student_id'],'name':st['name'],'error':str(e),'courses':[]}
        key=st['name'] if st['name'] not in out else '%s (%s)'%(st['name'],st['student_id']);out[key]=res
    # Build a compact assignment summary from the actual returned records.
    summary={
        'courses_total':0,'courses_with_assignments':0,'courses_with_no_assignments':0,
        'courses_without_score_links':0,'courses_with_errors':0,'total_assignments':0,
        'graded_assignments':0,'ungraded_assignments':0,'missing':0,'late':0,
        'incomplete':0,'exempt':0,'absent':0,'collected':0
    }
    for key,val in out.items():
        if key=='_meta' or not isinstance(val,dict):
            continue
        for course in val.get('courses',[]):
            summary['courses_total']+=1
            n=int(course.get('assignment_count') or 0)
            summary['total_assignments']+=n
            status=course.get('assignment_status')
            if status=='no_score_link': summary['courses_without_score_links']+=1
            elif status=='error': summary['courses_with_errors']+=1
            elif n: summary['courses_with_assignments']+=1
            else: summary['courses_with_no_assignments']+=1
            for arow in course.get('assignments',[]):
                if arow.get('percent') is None and not arow.get('letter'):
                    summary['ungraded_assignments']+=1
                else:
                    summary['graded_assignments']+=1
                for flag in ('missing','late','incomplete','exempt','absent','collected'):
                    if arow.get(flag): summary[flag]+=1
    out['_assignment_summary']=summary
    out['_meta']['version']=4

    def atomic_write(path, payload):
        if not path:
            return
        path=os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        tmp=path+'.tmp'
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump(payload,f,indent=2,ensure_ascii=False)
            f.write('\n')
        os.replace(tmp,path)
        debug('Wrote '+path)

    def compact_student(val):
        courses=[]
        for c in val.get('courses',[]):
            assignments=c.get('assignments',[]) or []
            graded=[x for x in assignments if x.get('percent') is not None or x.get('letter')]
            courses.append({
                'course':c.get('course'),
                'grade_raw':c.get('grade_raw',''),
                'grade_percent':c.get('grade_percent'),
                'grade_letter':c.get('grade_letter',''),
                'section_id':c.get('section_id'),
                'assignment_count':len(assignments),
                'graded_assignments':len(graded),
                'ungraded_assignments':len(assignments)-len(graded),
                'missing':sum(1 for x in assignments if x.get('missing')),
                'late':sum(1 for x in assignments if x.get('late')),
                'incomplete':sum(1 for x in assignments if x.get('incomplete')),
                'exempt':sum(1 for x in assignments if x.get('exempt')),
                'absent':sum(1 for x in assignments if x.get('absent')),
                'collected':sum(1 for x in assignments if x.get('collected')),
                'assignment_status':c.get('assignment_status'),
                'assignments':sorted(assignments,key=lambda x:((x.get('due') or '9999-99-99'),(x.get('name') or '').lower()))
            })
        return {
            'student_id':val.get('student_id'),
            'student_dcid':val.get('student_dcid'),
            'name':val.get('name'),
            'course_count':len(courses),
            'courses_with_assignments':sum(1 for c in courses if c['assignment_count']),
            'courses_without_assignments':sum(1 for c in courses if not c['assignment_count']),
            'assignment_count':sum(c['assignment_count'] for c in courses),
            'graded_assignments':sum(c['graded_assignments'] for c in courses),
            'ungraded_assignments':sum(c['ungraded_assignments'] for c in courses),
            'missing':sum(c['missing'] for c in courses),
            'late':sum(c['late'] for c in courses),
            'incomplete':sum(c['incomplete'] for c in courses),
            'exempt':sum(c['exempt'] for c in courses),
            'absent':sum(c['absent'] for c in courses),
            'collected':sum(c['collected'] for c in courses),
            'courses':courses
        }

    ha={'_meta':{**out['_meta'],'schema':'powerschool_ha_v1'},'students':{}}
    for key,val in out.items():
        if key.startswith('_') or not isinstance(val,dict) or 'courses' not in val:
            continue
        ha['students'][key]=compact_student(val)
    ha['summary']=out['_assignment_summary']
    if a.output: atomic_write(a.output,out)
    if a.ha_output: atomic_write(a.ha_output,ha)
    payload=ha if a.ha_only else out
    print(json.dumps(payload,indent=2 if a.pretty else None,ensure_ascii=False));return 0

if __name__=='__main__':sys.exit(main())

# Home Assistant adapter. The scraper functions above are the tested v4 logic;
# this wrapper supplies instance-style configuration for the HA integration.
class PowerSchoolClient:
    """Home Assistant adapter around the tested v4 PowerSchool protocol."""
    def __init__(self, base_url=None, username='', password='', term_start=None, term_end=None, photo_dir=None):
        global BASE_URL, PUBLIC_URL, LOGIN_URL, HOME_URL, LOOKUP_URL, TIMEOUT, DELAY, ACTIVE_TERM_START, ACTIVE_TERM_END, GET_ASSIGNMENTS, opener
        self.base_url=(base_url or BASE_URL).rstrip('/')
        self.username=username
        self.password=password
        self.term_start=term_start or current_school_year_range()[0]
        self.term_end=term_end or current_school_year_range()[1]
        self.photo_dir=photo_dir
        BASE_URL=self.base_url
        PUBLIC_URL=BASE_URL+'/public/'
        LOGIN_URL=BASE_URL+'/guardian/home.html'
        HOME_URL=LOGIN_URL
        LOOKUP_URL=''
        ACTIVE_TERM_START=self.term_start
        ACTIVE_TERM_END=self.term_end
        TIMEOUT=30
        DELAY=0.25
        GET_ASSIGNMENTS=True
        # Do not construct urllib's SSL opener here. Home Assistant calls the
        # config-flow constructor on the event loop; build_opener() invokes
        # SSLContext.load_default_certs()/set_default_verify_paths(), which are
        # blocking operations. The opener is created lazily inside the executor
        # when discover/fetch methods call request().
        jar=CookieJar()
        opener=None

    def _login_and_discover(self):
        r=login(self.username,self.password)
        if r['status'] in (401,403) or not login_success(r):
            raise PermissionError('PowerSchool login failed')
        students=find_students(r['body'])
        if not students:
            home=get(HOME_URL)
            if home['status'] in (401,403) or not login_success(home):
                raise PermissionError('PowerSchool login failed')
            students=find_students(home['body'])
        return students

    def discover_students(self):
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        students=self._login_and_discover()
        selected={str(x) for x in (selected_ids or [])}
        if selected:
            students=[s for s in students if str(s['student_id']) in selected]
        result={}
        for st in students:
            student=process_student(st,photo_dir=self.photo_dir)
            courses=student.get('courses', []) or []
            assignments=[a for c in courses for a in (c.get('assignments', []) or [])]
            graded=sum(1 for a in assignments if a.get('percent') is not None or a.get('letter'))
            numeric_grades=[c.get('grade_percent') for c in courses if c.get('grade_percent') is not None]
            student['course_count']=len(courses)
            student['courses_with_assignments']=sum(1 for c in courses if c.get('assignment_count', 0))
            student['courses_without_assignments']=sum(1 for c in courses if not c.get('assignment_count', 0))
            student['assignment_count']=len(assignments)
            student['graded_assignments']=graded
            student['ungraded_assignments']=len(assignments)-graded
            student['missing']=sum(1 for a in assignments if a.get('missing'))
            student['late']=sum(1 for a in assignments if a.get('late'))
            student['incomplete']=sum(1 for a in assignments if a.get('incomplete'))
            student['exempt']=sum(1 for a in assignments if a.get('exempt'))
            student['absent']=sum(1 for a in assignments if a.get('absent'))
            student['collected']=sum(1 for a in assignments if a.get('collected'))
            att_courses=[]
            abs_total=0
            tardy_total=0
            att_available=False
            for c in courses:
                a=c.get('absences')
                t=c.get('tardies')
                if a is not None or t is not None:
                    att_available=True
                a_val=int(a or 0) if a is not None else 0
                t_val=int(t or 0) if t is not None else 0
                abs_total += a_val
                tardy_total += t_val
                att_courses.append({
                    'course': c.get('course'),
                    'section_id': c.get('section_id'),
                    'absences': a if a is not None else None,
                    'tardies': t if t is not None else None,
                })
            headers=getattr(parse_grade_table, 'last_headers', None) or []
            student['attendance_headers']=headers
            student['attendance_abs_column']=getattr(parse_grade_table, 'last_abs_idx', None)
            student['attendance_tardy_column']=getattr(parse_grade_table, 'last_tardy_idx', None)
            if att_available:
                student['absences']=abs_total
                student['tardies']=tardy_total
                student['attendance_by_course']=att_courses
                student['attendance_status']='ok'
            else:
                student['absences']=None
                student['tardies']=None
                student['attendance_by_course']=[]
                student['attendance_status']='unavailable'
            student['grade_average']=(sum(numeric_grades)/len(numeric_grades)) if numeric_grades else None
            student['assignment_api_status']='ok' if any(c.get('assignment_status')=='ok' for c in courses) else (
                'no_data' if courses else 'no_courses'
            )
            student['identity_resolved']=bool(student.get('student_dcid'))
            result[st['name']]=student
        return {'students':result}

