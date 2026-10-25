rl':e.geturl(),'headers':e.headers,'body':text,'error':str(e)}
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
    if not 