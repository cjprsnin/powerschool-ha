from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import PowerSchoolClient
from .const import (
    CONF_PASSWORD, CONF_STUDENTS, CONF_UPDATE_INTERVAL, CONF_URL, CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL, DOMAIN, PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    client = PowerSchoolClient(
        base_url=data.get(CONF_URL),
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        photo_dir=hass.config.path('www', 'powerschool'),
    )

    async def async_update():
        try:
            return await hass.async_add_executor_job(client.fetch_students, data.get(CONF_STUDENTS, []))
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="PowerSchool",
        update_method=async_update,
        update_interval=timedelta(minutes=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
