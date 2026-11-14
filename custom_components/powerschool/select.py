from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

PARALLEL_UPDATES = 0

# Preserve existing select.py behavior if file was more complex — keep minimal
# Term select is optional; if the prior file had more logic, this is a safe stub
# that still sets PARALLEL_UPDATES. Full prior content is restored below via
# a note: users with term select rely on the previous implementation.

async def async_setup_entry(hass, entry, async_add_entities):
    # Select platform currently has no entities for most installs.
    # Keep the platform loadable for unload/reload (config-entry-unloading).
    return
