"""UI configuration for Menstruation."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_LUTEAL_PHASE,
    CONF_PERIOD_LENGTH,
    CONF_PROFILE_NAME,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_LUTEAL_PHASE,
    DEFAULT_PERIOD_LENGTH,
    DOMAIN,
)


def _schema(values: dict | None = None) -> vol.Schema:
    values = values or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PROFILE_NAME, default=values.get(CONF_PROFILE_NAME, "My cycle")
            ): vol.All(str, vol.Length(min=1, max=50)),
            vol.Required(
                CONF_CYCLE_LENGTH,
                default=values.get(CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH),
            ): vol.All(vol.Coerce(int), vol.Range(min=15, max=60)),
            vol.Required(
                CONF_PERIOD_LENGTH,
                default=values.get(CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=15)),
            vol.Required(
                CONF_LUTEAL_PHASE,
                default=values.get(CONF_LUTEAL_PHASE, DEFAULT_LUTEAL_PHASE),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=18)),
        }
    )


class MenstruationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create a cycle profile."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_PROFILE_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return MenstruationOptionsFlow(config_entry)


class MenstruationOptionsFlow(config_entries.OptionsFlow):
    """Update cycle defaults."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.entry, title=user_input[CONF_PROFILE_NAME]
            )
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=_schema({**self.entry.data, **self.entry.options})
        )
