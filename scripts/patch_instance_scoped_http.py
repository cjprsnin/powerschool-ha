#!/usr/bin/env python3
"""Refactor client_body HTTP state to thread-local sessions (true instance scope)."""
from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
cb = p.read_text(encoding="utf-8")

if "def _bind_tls_session" in cb and "def _S(name):" in cb:
    print("instance-scoped HTTP already applied")
    raise SystemExit(0)

if "import threading" not in cb:
    cb = cb.replace(
        "import argparse, getpass, html, json, os, re, sys, time",
        "import argparse, getpass, html, json, os, re, sys, time, threading",
        1,
    )

old_jar = None
for cand in [
    "jar=CookieJar(); opener=None\n_CLIENT_LOCK=threading.RLock()  # serialize HA scrapes sharing module globals",
    "jar=CookieJar(); opener=None",
]:
    if cand in cb:
        old_jar = cand
        break
if not old_jar:
    raise SystemExit("jar line not found")

new_jar = """jar=CookieJar(); opener=None
# Thread-local portal session: each executor worker binds its own URL/cookies.
# Module-level jar/opener remain as CLI defaults when no session is bound.
_tls=threading.local()

def _S(name):
    \"\"\"Read a session value from the active thread, else module default.\"\"\"
    if hasattr(_tls, name):
        return getattr(_tls, name)
    return globals()[name]

def _bind_tls_session(*, base_url, term_start, term_end, delay=None):
    \"\"\"Install a fresh portal session on this thread.\"\"\"
    base=(base_url or '').rstrip('/')
    _tls.BASE_URL=base
    _tls.PUBLIC_URL=base+'/public/'
    _tls.LOGIN_URL=base+'/guardian/home.html'
    _tls.HOME_URL=_tls.LOGIN_URL
    _tls.LOOKUP_URL=''
    _tls.ACTIVE_TERM_START=term_start
    _tls.ACTIVE_TERM_END=term_end
    _tls.TIMEOUT=30
    _tls.DELAY=float(delay if delay is not None else os.environ.get('POWERSCHOOL_DELAY','0.05'))
    _tls.GET_ASSIGNMENTS=True
    _tls.jar=CookieJar()
    _tls.opener=None
"""
cb = cb.replace(old_jar, new_jar, 1)

m = re.search(r"def _ensure_opener\(\):.*?\n(?=def request\()", cb, re.S)
if not m:
    raise SystemExit("_ensure_opener not found")
cb = cb[: m.start()] + """def _ensure_opener():
    # Prefer thread-local session (HA integration); fall back to module globals (CLI).
    if hasattr(_tls, 'opener'):
        if _tls.opener is None:
            _tls.jar=CookieJar()
            _tls.opener=build_opener(HTTPCookieProcessor(_tls.jar))
        return _tls.opener
    global jar, opener
    if opener is None:
        jar=CookieJar()
        opener=build_opener(HTTPCookieProcessor(jar))
    return opener

""" + cb[m.end() :]

m = re.search(
    r"def request\(url,method='GET',data=None,json_data=None,headers=None\):.*?\n(?=def get\()",
    cb,
    re.S,
)
if not m:
    raise SystemExit("request not found")
new_request = """def request(url,method='GET',data=None,json_data=None,headers=None):
    op=_ensure_opener()
    h={'User-Agent':UA,'Accept':'*/*'};h.update(headers or {});body=None
    if json_data is not None:
        body=json.dumps(json_data).encode();h.setdefault('Content-Type','application/json');h.setdefault('Accept','application/json, text/plain, */*')
    elif data is not None:
        body=urlencode(data).encode();h.setdefault('Content-Type','application/x-www-form-urlencoded')
    req=Request(url,data=body,headers=h,method=method);time.sleep(_S('DELAY'));debug('%s %s'%(method,url))
    try:
        r=op.open(req,timeout=_S('TIMEOUT'));raw=r.read();enc=r.headers.get_content_charset() or 'utf-8';text=raw.decode(enc,errors='replace');debug('HTTP %s %s (%d bytes)'%(r.status,r.geturl(),len(raw)))
        return {'status':r.status,'url':r.geturl(),'headers':r.headers,'body':text}
    except HTTPError as e:
        raw=e.read();text=raw.decode(e.headers.get_content_charset() or 'utf-8',errors='replace');return {'status':e.code,'url':e.geturl(),'headers':e.headers,'body':text,'error':str(e)}
    except URLError as e:return {'status':0,'url':url,'headers':{},'body':'','error':str(e)}

"""
cb = cb[: m.start()] + new_request + cb[m.end() :]

if "rr=opener.open(req,timeout=TIMEOUT)" in cb:
    cb = cb.replace(
        "rr=opener.open(req,timeout=TIMEOUT)",
        "rr=_ensure_opener().open(req,timeout=_S('TIMEOUT'))",
    )

session_names = [
    "BASE_URL",
    "PUBLIC_URL",
    "LOGIN_URL",
    "HOME_URL",
    "LOOKUP_URL",
    "TIMEOUT",
    "DELAY",
    "ACTIVE_TERM_START",
    "ACTIVE_TERM_END",
    "GET_ASSIGNMENTS",
]

def should_skip_line(line):
    s = line.strip()
    if s.startswith("#"):
        return True
    if s.startswith("def _S") or s.startswith("def _bind_tls") or s.startswith("def _ensure"):
        return True
    if "_tls." in line:
        return True
    return False

lines = cb.splitlines(keepends=True)
out = []
for line in lines:
    if should_skip_line(line):
        out.append(line)
        continue
    stripped = line.lstrip()
    skip = False
    for n in session_names + ["jar", "opener"]:
        if re.match(rf"^{n}\s*=", stripped):
            skip = True
            break
        if re.match(r"^global\b", stripped):
            skip = True
            break
    if skip:
        out.append(line)
        continue
    new = line
    for n in session_names:
        new = re.sub(
            rf"(?<!_S\(')(?<!_S\()(?<![\"'._])\b{n}\b(?!\s*=)",
            f"_S('{n}')",
            new,
        )
    out.append(new)
cb = "".join(out)

if "def _bind_session(self):" in cb:
    m = re.search(r"    def _bind_session\(self\):.*?(?=\n    def )", cb, re.S)
    if m:
        new_bind = """    def _bind_session(self):
        \"\"\"Bind this client's portal settings onto the current thread.\"\"\"
        _bind_tls_session(
            base_url=self.base_url,
            term_start=self.term_start,
            term_end=self.term_end,
            delay=os.environ.get('POWERSCHOOL_DELAY','0.05'),
        )

"""
        cb = cb[: m.start()] + new_bind + cb[m.end() :]
else:
    if "def discover_students(self):" in cb:
        cb = cb.replace(
            "    def discover_students(self):",
            """    def _bind_session(self):
        \"\"\"Bind this client's portal settings onto the current thread.\"\"\"
        _bind_tls_session(
            base_url=self.base_url,
            term_start=self.term_start,
            term_end=self.term_end,
            delay=os.environ.get('POWERSCHOOL_DELAY','0.05'),
        )

    def discover_students(self):""",
            1,
        )

cb = cb.replace(
    """    def discover_students(self):
        with _CLIENT_LOCK:
            self._bind_session()
            return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        with _CLIENT_LOCK:
            self._bind_session()
            return self._fetch_students_locked(selected_ids)

    def _fetch_students_locked(self, selected_ids=None):
        students=self._login_and_discover()""",
    """    def discover_students(self):
        self._bind_session()
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        self._bind_session()
        students=self._login_and_discover()""",
)

cb = cb.replace(
    """    def discover_students(self):
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        students=self._login_and_discover()""",
    """    def discover_students(self):
        self._bind_session()
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        self._bind_session()
        students=self._login_and_discover()""",
)

if "_CLIENT_LOCK" in cb and "with _CLIENT_LOCK" not in cb:
    cb = cb.replace(
        "_CLIENT_LOCK=threading.RLock()  # serialize HA scrapes sharing module globals\n",
        "",
    )

compile(cb, str(p), "exec")
p.write_text(cb, encoding="utf-8")
print("patched", p)
print("  _S:", "def _S(name):" in cb)
print("  tls bind:", "_bind_tls_session" in cb)
print("  lock gone:", "with _CLIENT_LOCK" not in cb)
