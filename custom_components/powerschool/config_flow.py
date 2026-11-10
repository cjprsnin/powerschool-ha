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
    CONF_DISTRICTS,
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


def _host_label(url: str) -> str:
    try:
        host = urlparse(url or "").hostname or ""
    except Exception:
        host = ""
    return host.split(".")[0] if host else ""


def _district_label(d: dict) -> str:
    name = (d.get(CONF_NAME) or "").strip()
    if name:
        return name
    return _host_label(d.get(CONF_URL) or "") or "District"


def _entry_title(data: dict) -> str:
    districts = data.get(CONF_DISTRICTS) or []
    if not districts and data.get(CONF_URL):
        districts = [data]
    labels = [_district_label(d) for d in districts if d]
    labels = [x for x in labels if x]
    if not labels:
        return "PowerSchool"
    if len(labels) == 1:
        return f"PowerSchool ({labels[0]})"
    return f"PowerSchool ({', '.join(labels[:3])})"


def _districts_from_data(data: dict) -> list[dict]:
    districts = data.get(CONF_DISTRICTS)
    if isinstance(districts, list) and districts:
        return [dict(d) for d in districts]
    if data.get(CONF_URL):
        return [
            {
                CONF_NAME: data.get(CONF_NAME) or "",
                CONF_URL: data[CONF_URL],
                CONF_USERNAME: data.get(CONF_USERNAME) or "",
                CONF_PASSWORD: data.get(CONF_PASSWORD) or "",
                CONF_STUDENTS: list(data.get(CONF_STUDENTS) or []),
            }
        ]
    return []


class CannotConnect(HomeAssistantError):
    pass


class InvalidAuth(HomeAssistantError):
    pass


class PowerSchoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One Home Assistant entry can hold multiple PowerSchool districts."""

    VERSION = 2

    def __init__(self) -> None:
        self._districts: list[dict] = []
        self._pending: dict = {}
        self._students: list = []
        self._interval = DEFAULT_UPDATE_INTERVAL

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])
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
                    if not self._districts and CONF_UPDATE_INTERVAL in user_input:
                        self._interval = user_input[CONF_UPDATE_INTERVAL]
                    self._pending = {
                        CONF_NAME: (user_input.get(CONF_NAME) or "").strip(),
                        CONF_URL: user_input[CONF_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    }
                    self._students = students
                    return await self.async_step_students()
            except PermissionError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        schema_fields: dict = {
            vol.Optional(CONF_NAME, default=""): str,
            vol.Required(CONF_URL): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
        if not self._districts:
            schema_fields[
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=5, max=1440))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
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
                self._districts.append(
                    {
                        CONF_NAME: self._pending.get(CONF_NAME) or "",
                        CONF_URL: self._pending[CONF_URL],
                        CONF_USERNAME: self._pending[CONF_USERNAME],
                        CONF_PASSWORD: self._pending[CONF_PASSWORD],
                        CONF_STUDENTS: [str(x) for x in selected],
                    }
                )
                return await self.async_step_add_another()

        return self.async_show_form(
            step_id="students",
            data_schema=vol.Schema(
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
            ),
            errors=errors,
        )

    async def async_step_add_another(self, user_input=None):
        if user_input is not None:
            if user_input.get("add_another"):
                self._pending = {}
                self._students = []
                return await self.async_step_user()
            return await self._async_finish()

        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema(
                {vol.Required("add_another", default=False): bool}
            ),
        )

    async def _async_finish(self):
        data = {
            CONF_DISTRICTS: list(self._districts),
            CONF_UPDATE_INTERVAL: self._interval,
        }
        d0 = self._districts[0]
        data[CONF_URL] = d0[CONF_URL]
        data[CONF_USERNAME] = d0[CONF_USERNAME]
        data[CONF_PASSWORD] = d0[CONF_PASSWORD]
        data[CONF_STUDENTS] = d0.get(CONF_STUDENTS) or []
        data[CONF_NAME] = d0.get(CONF_NAME) or ""

        uid_parts = sorted(
            f"{d[CONF_URL]}|{(d[CONF_USERNAME] or '').strip().lower()}"
            for d in self._districts
        )
        await self.async_set_unique_id("|".join(uid_parts))
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=_entry_title(data), data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        # HA 2024.4+: do not pass config_entry into OptionsFlow.__init__
        return PowerSchoolOptionsFlow()


class PowerSchoolOptionsFlow(config_entries.OptionsFlow):
    """Options: poll interval or add another district.

    Uses self.config_entry provided by Home Assistant (not set in __init__).
    """

    def __init__(self) -> None:
        self._pending: dict = {}
        self._students: list = []

    def _districts(self) -> list[dict]:
        return _districts_from_data(dict(self.config_entry.data))

    async def async_step_init(self, user_input=None):
        districts = self._districts()
        if user_input is not None:
            action = user_input.get("action", "save")
            if action == "add":
                return await self.async_step_add()
            new_data = dict(self.config_entry.data)
            new_data[CONF_DISTRICTS] = districts
            new_data[CONF_UPDATE_INTERVAL] = user_input.get(
                CONF_UPDATE_INTERVAL,
                new_data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            )
            if districts:
                d0 = districts[0]
                new_data[CONF_URL] = d0.get(CONF_URL)
                new_data[CONF_USERNAME] = d0.get(CONF_USERNAME)
                new_data[CONF_PASSWORD] = d0.get(CONF_PASSWORD)
                new_data[CONF_STUDENTS] = d0.get(CONF_STUDENTS) or []
                new_data[CONF_NAME] = d0.get(CONF_NAME) or ""
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, title=_entry_title(new_data)
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="save"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "save", "label": "Save settings"},
                                {"value": "add", "label": "Add another district"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                }
            ),
        )

    async def async_step_add(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_URL] = _normalize_url(user_input[CONF_URL])
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
                    self._pending = {
                        CONF_NAME: (user_input.get(CONF_NAME) or "").strip(),
                        CONF_URL: user_input[CONF_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    }
                    self._students = students
                    return await self.async_step_add_students()
            except PermissionError:
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="add",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=""): str,
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_add_students(self, user_input=None):
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
                districts = self._districts()
                districts.append(
                    {
                        CONF_NAME: self._pending.get(CONF_NAME) or "",
                        CONF_URL: self._pending[CONF_URL],
                        CONF_USERNAME: self._pending[CONF_USERNAME],
                        CONF_PASSWORD: self._pending[CONF_PASSWORD],
                        CONF_STUDENTS: [str(x) for x in selected],
                    }
                )
                new_data = dict(self.config_entry.data)
                new_data[CONF_DISTRICTS] = districts
                d0 = districts[0]
                new_data[CONF_URL] = d0.get(CONF_URL)
                new_data[CONF_USERNAME] = d0.get(CONF_USERNAME)
                new_data[CONF_PASSWORD] = d0.get(CONF_PASSWORD)
                new_data[CONF_STUDENTS] = d0.get(CONF_STUDENTS) or []
                new_data[CONF_NAME] = d0.get(CONF_NAME) or ""
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, title=_entry_title(new_data)
                )
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_students",
            data_schema=vol.Schema(
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
            ),
            errors=errors,
        )
