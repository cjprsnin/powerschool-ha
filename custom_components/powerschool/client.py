"""Minimal PowerSchool client — placeholder so integration loads."""
from __future__ import annotations

class PowerSchoolClient:
    def __init__(self, base_url=None, username="", password="", term_start=None, term_end=None, photo_dir=None):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username or ""
        self.password = password or ""
        self.term_start = term_start
        self.term_end = term_end
        self.photo_dir = photo_dir

    def discover_students(self):
        return []

    def fetch_students(self, selected_ids=None):
        return {"students": {}}

__all__ = ["PowerSchoolClient"]
