#!/usr/bin/env python3
"""Serialize PowerSchool scrapes and bind module globals per client fetch.

client_body still uses module-level BASE_URL/opener for the protocol helpers.
Until those are fully instance-scoped, a process-wide RLock around
discover/fetch prevents concurrent refresh/config-flow from clobbering
cookies and URLs mid-request.
"""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
text = p.read_text(encoding="utf-8")

if "_CLIENT_LOCK" in text and "_bind_session" in text:
    print("session lock already applied")
    raise SystemExit(0)

# import threading
if "import threading" not in text:
    text = text.replace(
        "import argparse, getpass, html, json, os, re, sys, time",
        "import argparse, getpass, html, json, os, re, sys, time, threading",
        1,
    )

# lock next to jar/opener
if "_CLIENT_LOCK" not in text:
    text = text.replace(
        "jar=CookieJar(); opener=None",
        "jar=CookieJar(); opener=None\n_CLIENT_LOCK=threading.RLock()  # serialize HA scrapes sharing module globals",
        1,
    )

old_init = '''    def __init__(self, base_url=None, username='', password='', term_start=None, term_end=None, photo_dir=None):
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
        DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))
        GET_ASSIGNMENTS=True
        # Do not construct urllib's SSL opener here. Home Assistant calls the
        # config-flow constructor on the event loop; build_opener() invokes
        # SSLContext.load_default_certs()/set_default_verify_paths(), which are
        # blocking operations. The opener is created lazily inside the executor
        # when discover/fetch methods call request().
        jar=CookieJar()
        opener=None'''

new_init = '''    def __init__(self, base_url=None, username='', password='', term_start=None, term_end=None, photo_dir=None):
        # Store config only. Module globals (BASE_URL/opener) are bound under
        # _CLIENT_LOCK at the start of discover/fetch so concurrent HA jobs
        # cannot interleave two districts mid-request.
        self.base_url=(base_url or BASE_URL).rstrip('/')
        self.username=username
        self.password=password
        self.term_start=term_start or current_school_year_range()[0]
        self.term_end=term_end or current_school_year_range()[1]
        self.photo_dir=photo_dir

    def _bind_session(self):
        """Apply this client\'s portal settings to module globals. Caller must hold _CLIENT_LOCK."""
        global BASE_URL, PUBLIC_URL, LOGIN_URL, HOME_URL, LOOKUP_URL, TIMEOUT, DELAY, ACTIVE_TERM_START, ACTIVE_TERM_END, GET_ASSIGNMENTS, opener, jar
        BASE_URL=self.base_url
        PUBLIC_URL=BASE_URL+'/public/'
        LOGIN_URL=BASE_URL+'/guardian/home.html'
        HOME_URL=LOGIN_URL
        LOOKUP_URL=''
        ACTIVE_TERM_START=self.term_start
        ACTIVE_TERM_END=self.term_end
        TIMEOUT=30
        DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))
        GET_ASSIGNMENTS=True
        # Fresh cookie jar per bound session; opener stays lazy (executor only).
        jar=CookieJar()
        opener=None'''

if old_init not in text:
    # try with DELAY=0.25 variant
    old_init2 = old_init.replace(
        'DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))',
        'DELAY=0.25',
    )
    if old_init2 in text:
        old_init = old_init2
    else:
        raise SystemExit("PowerSchoolClient.__init__ block not found — layout changed")

text = text.replace(old_init, new_init, 1)

# Wrap discover + fetch
old_discover = '''    def discover_students(self):
        return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        students=self._login_and_discover()'''

new_discover = '''    def discover_students(self):
        with _CLIENT_LOCK:
            self._bind_session()
            return self._login_and_discover()

    def fetch_students(self, selected_ids=None):
        with _CLIENT_LOCK:
            self._bind_session()
            return self._fetch_students_locked(selected_ids)

    def _fetch_students_locked(self, selected_ids=None):
        students=self._login_and_discover()'''

if old_discover not in text:
    raise SystemExit("discover/fetch block not found")
text = text.replace(old_discover, new_discover, 1)

# Indent body of fetch_students was not changed - _fetch_students_locked continues same body
# The original fetch_students body remains at same indent under _fetch_students_locked — good.

compile(text, str(p), "exec")
p.write_text(text, encoding="utf-8")
print("patched", p)
print("  lock:", "_CLIENT_LOCK" in text)
print("  bind:", "_bind_session" in text)
print("  locked fetch:", "_fetch_students_locked" in text)
"""
