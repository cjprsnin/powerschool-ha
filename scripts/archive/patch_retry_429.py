#!/usr/bin/env python3
"""Add HTTP 429 + Retry-After handling to client_body.request()."""
from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
cb = p.read_text(encoding="utf-8")

if "max_retries" in cb and "Retry-After" in cb and "status == 429" in cb:
    print("429 handling already present")
    raise SystemExit(0)

old = '''def request(url,method='GET',data=None,json_data=None,headers=None):
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
    except URLError as e:return {'status':0,'url':url,'headers':{},'body':'','error':str(e)}'''

new = '''def request(url,method='GET',data=None,json_data=None,headers=None,max_retries=3):
    """HTTP helper with DELAY and polite 429 / Retry-After backoff."""
    op=_ensure_opener()
    h={'User-Agent':UA,'Accept':'*/*'};h.update(headers or {});body=None
    if json_data is not None:
        body=json.dumps(json_data).encode();h.setdefault('Content-Type','application/json');h.setdefault('Accept','application/json, text/plain, */*')
    elif data is not None:
        body=urlencode(data).encode();h.setdefault('Content-Type','application/x-www-form-urlencoded')
    last=None
    for attempt in range(max_retries + 1):
        req=Request(url,data=body,headers=h,method=method)
        time.sleep(_S('DELAY'))
        debug('%s %s (attempt %d)'%(method,url,attempt+1))
        try:
            r=op.open(req,timeout=_S('TIMEOUT'))
            raw=r.read()
            enc=r.headers.get_content_charset() or 'utf-8'
            text=raw.decode(enc,errors='replace')
            debug('HTTP %s %s (%d bytes)'%(r.status,r.geturl(),len(raw)))
            return {'status':r.status,'url':r.geturl(),'headers':r.headers,'body':text}
        except HTTPError as e:
            raw=e.read()
            text=raw.decode(e.headers.get_content_charset() or 'utf-8',errors='replace')
            last={'status':e.code,'url':e.geturl(),'headers':e.headers,'body':text,'error':str(e)}
            if e.code == 429 and attempt < max_retries:
                ra = None
                try:
                    ra = e.headers.get('Retry-After') or e.headers.get('retry-after')
                except Exception:
                    ra = None
                wait = 5.0
                if ra:
                    try:
                        wait = float(str(ra).strip())
                    except ValueError:
                        wait = 5.0
                wait = max(1.0, min(wait, 60.0))
                debug('HTTP 429 — sleeping %.1fs then retry'%wait)
                time.sleep(wait)
                continue
            return last
        except URLError as e:
            last={'status':0,'url':url,'headers':{},'body':'','error':str(e)}
            if attempt < max_retries:
                wait = min(2 ** attempt, 15)
                debug('URLError %s — sleep %ss'% (e, wait))
                time.sleep(wait)
                continue
            return last
    return last or {'status':0,'url':url,'headers':{},'body':'','error':'request failed'}'''

if old not in cb:
    # Try matching after instance-scoped rewrite (already has _S)
    m = re.search(
        r"def request\(url,method='GET',data=None,json_data=None,headers=None\):.*?\n(?=def get\()",
        cb,
        re.S,
    )
    if not m:
        raise SystemExit("request() block not found — update patch manually")
    cb = cb[: m.start()] + new + "\n" + cb[m.end() :]
else:
    cb = cb.replace(old, new, 1)

compile(cb, str(p), "exec")
p.write_text(cb, encoding="utf-8")
print("patched 429 handling into", p)
