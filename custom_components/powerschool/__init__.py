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
    if base_url and base_url != data.get(CONF_URL):
        data[CONF_URL] = base_url
        hass.config_entries.async_update_entry(entry, data=data)

    client = PowerSchoolClient(
        base_url=data.get(CONF_URL),
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        photo_dir=hass.config.path("www", "powerschool"),
    )

    async def async_update():
        # Retry transient network failures (remote closed connection, timeouts).
        last_err = None
        start = time.monotonic()
        for attempt in range(3):
            try:
                result = await hass.async_add_executor_job(
                    client.fetch_students, data.get(CONF_STUDENTS, [])
                )

                # Normalize result shape
                if not isinstance(result, dict):
                    result = {"students": result}
                students = result.get("students") or {}

                # Persist grade history across updates
                history_store = hass.data.setdefault(DOMAIN, {}).setdefault(
                    "grade_history", {}
                )

                for _name, student in students.items():
                    # Upcoming / due-soon (ungraded only)
                    due_soon, upcoming = collect_upcoming(student)
                    student["due_soon_assignments"] = due_soon
                    student["upcoming_assignments"] = upcoming
                    student["due_soon_count"] = len(due_soon)
                    student["upcoming_count"] = len(upcoming)

                    # Grade history per course
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

                # Preserve any extra top-level keys from the client
                result["students"] = students
                result["update_duration_ms"] = int(
                    (time.monotonic() - start) * 1000
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
                        "broken pipe",
                    )
                )
                if not transient or attempt >= 2:
                    raise UpdateFailed(str(err)) from err
                _LOGGER.warning(
                    "PowerSchool update attempt %s failed (%s); retrying",
                    attempt + 1,
                    err,
                )
                await asyncio.sleep(2 * (attempt + 1))
        raise UpdateFailed(str(last_err)) from last_err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="PowerSchool",
        update_method=async_update,
        update_interval=timedelta(
            minutes=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def async_refresh_service(call: ServiceCall) -> None:
        for coord in list(hass.data.get(DOMAIN, {}).values()):
            await coord.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            async_refresh_service,
            schema=vol.Schema({}),
        )

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, SERVICE_REFRESH):
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unloaded
