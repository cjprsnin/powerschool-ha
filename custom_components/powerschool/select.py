from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _slug(value: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(value)).strip('_')


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PowerSchoolStudentSelect(coordinator, entry.entry_id)])


class PowerSchoolStudentSelect(CoordinatorEntity, SelectEntity):
    _attr_icon = "mdi:account-school"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "PowerSchool Student"
        self._attr_unique_id = f"powerschool_{entry_id}_student_selector"
        self._selected = None

    @property
    def options(self):
        return list(self.coordinator.data.get("students", {}).keys())

    @property
    def current_option(self):
        options = self.options
        if self._selected in options:
            return self._selected
        return options[0] if options else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            return
        self._selected = option
        self.async_write_ha_state()
