"""Shared entity base class."""

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import CONF_PROFILE_NAME, DOMAIN
from .runtime import MenstruationRuntime


class MenstruationEntity(Entity):
    """Base entity attached to a profile device."""

    _attr_has_entity_name = True

    def __init__(self, runtime: MenstruationRuntime, key: str) -> None:
        self.runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_{key}"
        profile = runtime.settings[CONF_PROFILE_NAME]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=profile,
            manufacturer="Menstruation",
            model="Cycle profile",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.runtime.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
