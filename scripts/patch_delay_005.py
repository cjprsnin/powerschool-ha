#!/usr/bin/env python3
"""Lower PowerSchool inter-request DELAY default from 0.25s to 0.05s."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "custom_components/powerschool/client_body.py"
text = p.read_text(encoding="utf-8")
orig = text
text = text.replace(
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','.25'))",
    "DELAY=float(os.environ.get('POWERSCHOOL_DELAY','0.05'))",
)
text = text.replace("DELAY=0.25", 'DELAY=float(os.environ.get("POWERSCHOOL_DELAY","0.05"))')
if text == orig:
    # already patched or different quote style
    text2 = text.replace(".25", "0.05") if "POWERSCHOOL_DELAY" in text else text
    if "0.05" not in text and "POWERSCHOOL_DELAY" in text:
        import re
        text = re.sub(
            r"POWERSCHOOL_DELAY',\s*\.?25" ,
            "POWERSCHOOL_DELAY','0.05",
            text,
        )
        text = re.sub(
            r'POWERSCHOOL_DELAY",\s*\.?25',
            'POWERSCHOOL_DELAY","0.05',
            text,
        )
if "0.05" not in text:
    raise SystemExit("patch failed: DELAY 0.05 not found after replace")
p.write_text(text, encoding="utf-8")
print("patched", p)
