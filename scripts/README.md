# Scripts

One-off historical patch scripts used while evolving `client_body.py`.

**Prefer applying these (in order) on a checkout that still needs them:**

1. `patch_client_body_speed.py` — DELAY 0.05 + photo-miss cache  
2. `patch_batch_assignments.py` — multi-section assignment lookup  
3. `patch_instance_scoped_http.py` — thread-local session (preferred over session lock)  
4. `patch_retry_429.py` — HTTP 429 + `Retry-After` retries  

Once those land in `custom_components/powerschool/client_body.py` and are pushed, the other `patch_*.py` / `fix_*.py` files are **history only** and safe to delete from a local clone. They are kept in the repo briefly for reference; do not re-run obsolete attendance/portal patches on a current tree.

Empty / no-op: `apply_card_polish.py`.
