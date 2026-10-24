from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .client import PowerSchoolClient
from .const import (
    CONF_STUDENTS, CONF_UPDATE_INTERVAL, CONF_URL,
    DEFAULT_UPDATE_INTERVAL, DOMAIN,
)


class CannotConnect(HomeAssistantError):
    pass


class InvalidAuth(HomeAssistantError):
    pass


class PowerSchoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}
        self._students = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await self.async_set_unique_id(
                    f"{user_input[CONF_URL].rstrip('/')}|{user_input[CONF_USERNAME].strip().lower()}"
                )
                self._abort_if_unique_id_configured()
                client = PowerSchoolClient(
                    user_input[CONF_URL],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                students = await self.hass.async_add_executor_job(client.discover_students)
                if not students:
                    errors["base"] = "no_students"
                else:
                    self._data = dict(user_input)
                    self._students = students
                    return await self.async_step_students()
            except PermissionError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_URL): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=DEFAULT_UPDATE_INTERVAL,
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_students(self, user_input=None):
        if user_input is not None:
            self._data[CONF_STUDENTS] = [str(x) for x in user_input[CONF_STUDENTS]]
            return self.async_create_entry(title="PowerSchool", data=self._data)

        options = [
            {"value": str(s["student_id"]), "label": str(s["name"])}
            for s in self._students
            if s.get("student_id") is not None
        ]
        schema = vol.Schema({
            vol.Required(CONF_STUDENTS, default=[o["value"] for o in options]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        })
        return self.async_show_form(step_id="students", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerSchoolOptionsFlow(config_entry)


class PowerSchoolOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        data = dict(self.config_entry.data)
        if user_input is not None:
            new_data = dict(data)
            new_data.update(user_input)
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        client = PowerSchoolClient(
            data[CONF_URL], data[CONF_USERNAME], data[CONF_PASSWORD]
        )
        students = await self.hass.async_add_executor_job(client.discover_students)
        options = [
            {"value": str(s["student_id"]), "label": str(s["name"])}
            for s in students
            if s.get("student_id") is not None
        ]
        schema = vol.Schema({
            vol.Required(CONF_URL, default=data[CONF_URL]): str,
            vol.Required(CONF_USERNAME, default=data[CONF_USERNAME]): str,
            vol.Required(CONF_PASSWORD, default=data[CONF_PASSWORD]): str,
            vol.Required(
                CONF_STUDENTS,
                default=[str(x) for x in data.get(CONF_STUDENTS, [o["value"] for o in options])],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
