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
    text=html.unescape(str(v or '')).strip()
    m=re.fullmatch(r'0*001(\d+)',text)
    if m:
        return m.group(1).lstrip('0') or '0'
    m=re.search(r'(\d+)',text)
    return m.group(1) if m else None
