#!/usr/bin/env python3
"""Force Absences/Tardies from the last two cells when headers end with those labels."""
from pathlib import Path
import sys

path = Path("custom_components/powerschool/client_body.py")
code = path.read_text()

old = """        use_abs, use_tardy, use_att = abs_idx, tardy_idx, att_idx
        nvals=len(values)
        if (use_abs is not None and use_abs >= nvals) or (use_tardy is not None and use_tardy >= nvals):
            if nvals >= 2 and abs_idx is not None and tardy_idx is not None:
                use_abs, use_tardy = nvals-2, nvals-1
            elif nvals >= 1 and abs_idx is not None:
                use_abs = nvals-1
        absences=_cell_count(use_abs)
        tardies=_cell_count(use_tardy)
        if absences is None and use_att is not None and use_abs is None:
            absences=_cell_count(use_att if use_att < nvals else nvals-1)
"""

new = """        use_abs, use_tardy, use_att = abs_idx, tardy_idx, att_idx
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
"""

if old not in code:
    if "headers_end_with_att" in code:
        print("Already patched")
        sys.exit(0)
    sys.exit("Expected cell block not found")

code = code.replace(old, new, 1)
compile(code, "client_body.py", "exec")
path.write_text(code)
print("Patched", path)
