"""Menstruation integration setup."""

from __future__ import annotations

from datetime import date
from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_END_DATE,
    ATTR_START_DATE,
    DOMAIN,
    PLATFORMS,
    SERVICE_DELETE_PERIOD,
    SERVICE_RECORD_PERIOD,
)
from .runtime import MenstruationRuntime

MenstruationConfigEntry = ConfigEntry[MenstruationRuntime]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register record management actions."""

    def get_runtime(call: ServiceCall) -> MenstruationRuntime:
        entry = hass.config_entries.async_get_entry(call.data[ATTR_CONFIG_ENTRY_ID])
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("Menstruation profile not found")
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError("Menstruation profile is not loaded")
        return cast(MenstruationConfigEntry, entry).runtime_data

    async def async_record_period(call: ServiceCall) -> None:
        runtime = get_runtime(call)
        start: date = call.data[ATTR_START_DATE]
        end: date | None = call.data.get(ATTR_END_DATE)
        if start > dt_util.now().date():
            raise ServiceValidationError("Start date cannot be in the future")
        if end is not None and end < start:
            raise ServiceValidationError("End date cannot be before start date")
        if end is not None and (end - start).days >= 15:
            raise ServiceValidationError("A recorded period cannot exceed 15 days")
        await runtime.async_record(start, end)

    async def async_delete_period(call: ServiceCall) -> None:
        runtime = get_runtime(call)
        if not await runtime.async_delete(call.data[ATTR_START_DATE]):
            raise ServiceValidationError("No record exists for that start date")

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_PERIOD,
        async_record_period,
        schema=vol.Schema(
            {
                vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Required(ATTR_START_DATE): cv.date,
                vol.Optional(ATTR_END_DATE): cv.date,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_PERIOD,
        async_delete_period,
        schema=vol.Schema(
            {
                vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Required(ATTR_START_DATE): cv.date,
            }
        ),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MenstruationConfigEntry) -> bool:
    """Set up one profile."""
    runtime = MenstruationRuntime(hass, entry)
    await runtime.async_load()
    entry.runtime_data = runtime
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    @callback
    def midnight_refresh(now) -> None:
        async_dispatcher_send(hass, runtime.signal)

    entry.async_on_unload(
        async_track_time_change(hass, midnight_refresh, hour=0, minute=0, second=5)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MenstruationConfigEntry) -> bool:
    """Unload a profile."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: MenstruationConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
