#!/usr/bin/env python3
"""Skip student photo re-download when a local file already exists."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text(encoding="utf-8")

if "Using cached student photo" in code:
    print("photo cache already present")
    sys.exit(0)

start = code.find("def save_student_photo")
if start < 0:
    sys.exit("save_student_photo not found")
end = code.find("\ndef ", start + 1)
if end < 0:
    sys.exit("could not find end of save_student_photo")
old = code[start:end]

idx = old.find("    try:")
if idx < 0:
    sys.exit("try block not found in save_student_photo")
body = old[idx:].replace("str(student_id)", "sid")

prefix = '''def save_student_photo(photo_url, student_id, photo_dir, force=False):
    """Download an authenticated student photo into a local web directory.

    Skips the network download when a non-empty photo file already exists
    for this student (set force=True to refresh).
    """
    if not photo_dir:
        return None
    sid=str(student_id)
    # Reuse cached photo when present (avoids a portal round-trip every refresh).
    if not force:
        for ext in ('.jpg','.jpeg','.png','.webp','.gif'):
            existing=os.path.join(photo_dir,sid+ext)
            try:
                if os.path.isfile(existing) and os.path.getsize(existing)>0:
                    debug('Using cached student photo %s'%existing)
                    return '/local/powerschool/'+sid+ext
            except OSError:
                pass
    if not photo_url:
        return None
'''

new = prefix + body
code2 = code[:start] + new + code[end:]
compile(code2, "client_body.py", "exec")
path.write_text(code2, encoding="utf-8")
print("applied photo cache skip")
print("OK")
