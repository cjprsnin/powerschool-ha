from __future__ import annotations

from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .client import PowerSchoolClient
from .const import (
    CONF_NAME,
    CONF_STUDENTS,
    CONF_UPDATE_INTERVAL,
    CONF_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if "://" not in url:
        url = "https://" + url
    return url.rstrip("/")


def _entry_title(data: dict) -> str:
    """Human title for a config entry (supports multiple districts)."""
    name = (data.get(CONF_NAME) or "").strip()
    if name:
        return f"PowerSchool ({name})"
    url = data.get(CONF_URL) or ""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    if host:
        short = host.split(".")[0]
        return f"PowerSchool ({short})"
    return "PowerSchool"


class CannotConnect(HomeAssistantError):
    pass


class InvalidAuth(HomeAssistantError):
    pass


class PowerSchoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PowerSchool Grades."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}
        self._students: list = []

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])
                await self.async_set_unique_id(
                    f"{user_input[CONF_URL]}|{user_input[CONF_USERNAME].strip().lower()}"
                )
                self._abort_if_unique_id_configured()
                client = PowerSchoolClient(
                    user_input[CONF_URL],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                students = await self.hass.async_add_executor_job(
                    client.discover_students
                )
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

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Optional(CONF_NAME, default=""): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_students(self, user_input=None):
        errors: dict[str, str] = {}
        options = [
            {"value": str(s["student_id"]), "label": str(s["name"])}
            for s in self._students
            if s.get("student_id") is not None
        ]
        if user_input is not None:
            selected = user_input.get(CONF_STUDENTS) or []
            if not selected:
                errors["base"] = "no_students"
            else:
                self._data[CONF_STUDENTS] = selected
                return self.async_create_entry(
                    title=_entry_title(self._data), data=self._data
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_STUDENTS,
                    default=[o["value"] for o in options],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="students", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerSchoolOptionsFlow(config_entry)


class PowerSchoolOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        data = dict(self.config_entry.data)
        if user_input is not None:
            user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])
            new_data = dict(data)
            new_data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, title=_entry_title(new_data)
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        students: list = []
        try:
            client = PowerSchoolClient(
                data[CONF_URL], data[CONF_USERNAME], data[CONF_PASSWORD]
            )
            students = await self.hass.async_add_executor_job(
                client.discover_students
            )
        except Exception:
            students = []

        options = [
            {"value": str(s["student_id"]), "label": str(s["name"])}
            for s in students
            if s.get("student_id") is not None
        ]
        if not options:
            options = [
                {"value": str(x), "label": str(x)}
                for x in data.get(CONF_STUDENTS, [])
            ]

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=data.get(CONF_URL, "")): str,
                vol.Optional(CONF_NAME, default=data.get(CONF_NAME, "")): str,
                vol.Required(
                    CONF_USERNAME, default=data.get(CONF_USERNAME, "")
                ): str,
                vol.Required(
                    CONF_PASSWORD, default=data.get(CONF_PASSWORD, "")
                ): str,
                vol.Required(
                    CONF_STUDENTS,
                    default=[
                        str(x)
                        for x in data.get(
                            CONF_STUDENTS, [o["value"] for o in options]
                        )
                    ],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=data.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
