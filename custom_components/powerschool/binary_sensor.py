from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _slug(value):
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _student_key(name, student):
    return f"{_slug(name)}_{student.get('student_id', '')}"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for name, student in coordinator.data.get("students", {}).items():
        key = _student_key(name, student)
        entities.append(PowerSchoolFlagBinarySensor(coordinator, name, student, key, "missing", "Has Missing Work"))
        entities.append(PowerSchoolFlagBinarySensor(coordinator, name, student, key, "late", "Has Late Work"))
    async_add_entities(entities)


class PowerSchoolFlagBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, student_name, student, key, field, label):
        super().__init__(coordinator)
        self._student_name = student_name
        self._student_id = str(student.get("student_id", ""))
        self._field = field
        self._attr_name = f"PowerSchool {student_name} {label}"
        self._attr_unique_id = f"powerschool_{key}_has_{field}"
        self._attr_icon = "mdi:alert-circle" if field == "missing" else "mdi:clock-alert"

    def _student(self):
        return self.coordinator.data.get("students", {}).get(self._student_name, {})

    @property
    def is_on(self):
        return int(self._student().get(self._field) or 0) > 0

    @property
    def entity_picture(self):
        return self._student().get("photo_url")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"student_{self._student_id}")},
            "name": f"PowerSchool {self._student_name}",
            "manufacturer": "PowerSchool",
            "model": "Student",
        }

    @property
    def extra_state_attributes(self):
        student = self._student()
        return {
            "count": int(student.get(self._field) or 0),
            "student_id": student.get("student_id"),
            "photo_url": student.get("photo_url"),
        }
