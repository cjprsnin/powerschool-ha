from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import logging
import time
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import voluptuous as vol

from .client import PowerSchoolClient
from .const import (
    CONF_DISTRICTS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_STUDENTS,
    CONF_UPDATE_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_REFRESH,
)
from .helpers import collect_upcoming, update_grade_history

_LOGGER = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize PowerSchool base URL (scheme required, no trailing slash)."""
    url = (url or "").strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    path = (parsed.path or "").rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = dict(entry.data)
    base_url = normalize_url(data.get(CONF_URL, ""))
    changed = False
    if base_url and base_url != data.get(CONF_URL):
        data[CONF_URL] = base_url
        changed = True
    if not data.get(CONF_DISTRICTS) and data.get(CONF_URL):
        data[CONF_DISTRICTS] = [
            {
                CONF_NAME: data.get(CONF_NAME) or "",
                CONF_URL: data.get(CONF_URL),
                CONF_USERNAME: data.get(CONF_USERNAME),
                CONF_PASSWORD: data.get(CONF_PASSWORD),
                CONF_STUDENTS: list(data.get(CONF_STUDENTS) or []),
            }
        ]
        changed = True
    if changed:
        hass.config_entries.async_update_entry(entry, data=data)

    photo_dir = hass.config.path("www", "powerschool")

    def _district_list(cfg: dict) -> list[dict]:
        districts = cfg.get(CONF_DISTRICTS)
        if isinstance(districts, list) and districts:
            return districts
        if cfg.get(CONF_URL):
            return [
                {
                    CONF_NAME: cfg.get(CONF_NAME) or "",
                    CONF_URL: cfg.get(CONF_URL),
                    CONF_USERNAME: cfg.get(CONF_USERNAME),
                    CONF_PASSWORD: cfg.get(CONF_PASSWORD),
                    CONF_STUDENTS: cfg.get(CONF_STUDENTS) or [],
                }
            ]
        return []

    def _label(d: dict) -> str:
        name = (d.get(CONF_NAME) or "").strip()
        if name:
            return name
        try:
            host = urlparse(d.get(CONF_URL) or "").hostname or ""
        except Exception:
            host = ""
        return (host.split(".")[0] if host else "") or "District"

    async def async_update():
        last_err = None
        start = time.monotonic()
        cfg = dict(entry.data)
        districts = _district_list(cfg)
        multi = len(districts) > 1
        for attempt in range(3):
            try:
                students = {}
                for dist in districts:
                    client = PowerSchoolClient(
                        base_url=normalize_url(dist.get(CONF_URL) or ""),
                        username=dist.get(CONF_USERNAME),
                        password=dist.get(CONF_PASSWORD),
                        photo_dir=photo_dir,
                    )
                    result = await hass.async_add_executor_job(
                        client.fetch_students, dist.get(CONF_STUDENTS, [])
                    )
                    if not isinstance(result, dict):
                        result = {"students": result}
                    batch = result.get("students") or {}
                    label = _label(dist)
                    for name, student in batch.items():
                        if not isinstance(student, dict):
                            continue
                        student = dict(student)
                        student["district"] = label
                        student["district_url"] = dist.get(CONF_URL)
                        key = f"{label} {name}" if multi else name
                        students[key] = student

                history_store = hass.data.setdefault(DOMAIN, {}).setdefault(
                    "grade_history", {}
                )

                for _name, student in students.items():
                    due_soon, upcoming = collect_upcoming(student)
                    student["due_soon_assignments"] = due_soon
                    student["upcoming_assignments"] = upcoming
                    student["due_soon_count"] = len(due_soon)
                    student["upcoming_count"] = len(upcoming)

                    for course in student.get("courses") or []:
                        section_id = str(
                            course.get("section_id") or course.get("course") or ""
                        )
                        key = f"{student.get('student_id')}:{section_id}"
                        prev_hist = history_store.get(key, [])
                        percent = course.get("grade_percent")
                        new_hist, grade_attrs = update_grade_history(
                            prev_hist, percent
                        )
                        history_store[key] = new_hist
                        course.update(grade_attrs)

                result = {"students": students}
                duration_ms = int((time.monotonic() - start) * 1000)
                result["update_duration_ms"] = duration_ms
                _LOGGER.info(
                    "PowerSchool refresh finished in %sms (%s student(s))",
                    duration_ms,
                    len(students),
                )
                return result

            except Exception as err:
                last_err = err
                msg = str(err).lower()
                transient = any(
                    t in msg
                    for t in (
                        "remote end closed",
                        "connection reset",
                        "timed out",
                        "timeout",
                        "temporarily unavailable",
                        "connection aborted",
                    )
                )
                if attempt < 2 and transient:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise UpdateFailed(str(err)) from err
        raise UpdateFailed(str(last_err) if last_err else "update failed")

    interval = max(
        5, int(data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL) or DEFAULT_UPDATE_INTERVAL)
    )
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"powerschool_{entry.entry_id}",
        update_method=async_update,
        update_interval=timedelta(minutes=interval),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    coordinator.async_set_updated_data({"students": {}})

    async def _bg_first_refresh() -> None:
        try:
            await coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.warning("PowerSchool first refresh failed: %s", err)

    hass.async_create_background_task(
        _bg_first_refresh(), name=f"powerschool_first_refresh_{entry.entry_id}"
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_refresh(call: ServiceCall) -> None:
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        still_loaded = any(
            isinstance(v, DataUpdateCoordinator)
            for v in hass.data.get(DOMAIN, {}).values()
        )
        if not still_loaded and hass.services.has_service(DOMAIN, SERVICE_REFRESH):
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unloaded
