#!/usr/bin/env python3
"""Apply DELAY 0.05 + 7-day photo-miss cache to client_body.py."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
text = p.read_text(encoding="utf-8")
orig = text

text = text.replace(
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','.25'))",
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','0.05'))",
)
text = text.replace(
    "DELAY=0.25",
    'DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))',
)

old = """    if not local_photo and photo_dir:
        # Fallback: common PowerSchool studentphoto endpoints using resolved IDs
        candidates=candidate_photo_urls(sid, student_frn=student_frn, student_dcid=student_dcid)
        src_url, local_photo = try_save_photo_candidates(candidates, sid, photo_dir)
        if src_url:
            result['photo_source_url']=src_url
    if local_photo:
        result['photo_url']=local_photo
    else:
        debug('No student photo found for %s (id=%s frn=%s dcid=%s)'%(name,sid,student_frn,student_dcid))"""

new = """    if not local_photo and photo_dir:
        # Fallback: common PowerSchool studentphoto endpoints using resolved IDs.
        # Cache misses for 7 days so we do not hammer dead photo URLs every poll.
        miss_path=os.path.join(photo_dir, '%s.none'%sid)
        skip_candidates=False
        if os.path.isfile(miss_path):
            try:
                age=time.time()-os.path.getmtime(miss_path)
                if age < 7*86400:
                    skip_candidates=True
                    debug('Skipping photo candidates for %s (miss cached %.1fd)'%(sid, age/86400.0))
            except OSError:
                pass
        if not skip_candidates:
            candidates=candidate_photo_urls(sid, student_frn=student_frn, student_dcid=student_dcid)
            src_url, local_photo = try_save_photo_candidates(candidates, sid, photo_dir)
            if src_url:
                result['photo_source_url']=src_url
            if local_photo:
                try:
                    if os.path.isfile(miss_path):
                        os.remove(miss_path)
                except OSError:
                    pass
            else:
                try:
                    os.makedirs(photo_dir, exist_ok=True)
                    with open(miss_path, 'w') as f:
                        f.write(str(int(time.time())))
                except OSError as e:
                    debug('Could not write photo miss marker: %s'%e)
    if local_photo:
        result['photo_url']=local_photo
    else:
        debug('No student photo found for %s (id=%s frn=%s dcid=%s)'%(name,sid,student_frn,student_dcid))"""

if old in text:
    text = text.replace(old, new, 1)
elif "miss_path=os.path.join(photo_dir" in text:
    print("photo-miss already applied")
else:
    raise SystemExit("photo block not found — client_body layout changed")

if text == orig and "0.05" not in text:
    raise SystemExit("no changes applied")

compile(text, str(p), "exec")
p.write_text(text, encoding="utf-8")
print("patched", p)
print("  DELAY 0.05:", "POWERSCHOOL_DELAY','0.05" in text or 'POWERSCHOOL_DELAY","0.05' in text)
print("  photo miss:", "miss_path" in text)
