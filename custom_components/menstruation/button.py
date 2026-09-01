"""Button for recording a period from the device page."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MenstruationEntity
from .runtime import MenstruationRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[MenstruationRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up period recording buttons."""
    async_add_entities(
        [
            StartPeriodButton(entry.runtime_data),
            EndPeriodButton(entry.runtime_data),
            RecordPeriodButton(entry.runtime_data),
        ]
    )


class PeriodStateButton(MenstruationEntity, ButtonEntity):
    """Button whose availability follows the ongoing period state."""

    _available_when_ongoing: bool

    def __init__(self, runtime: MenstruationRuntime, key: str) -> None:
        super().__init__(runtime, key)
        self._sync_availability()

    def _sync_availability(self) -> None:
        """Update availability and invalidate Home Assistant's cached value."""
        is_ongoing = self.runtime.ongoing_record is not None
        self._attr_available = is_ongoing == self._available_when_ongoing

    @callback
    def _handle_update(self) -> None:
        """Refresh availability before publishing the new state."""
        self._sync_availability()
        super()._handle_update()


class StartPeriodButton(PeriodStateButton):
    """Start an ongoing period today."""

    _attr_translation_key = "start_period"
    _attr_icon = "mdi:play"
    _available_when_ongoing = False

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "start_period")

    async def async_press(self) -> None:
        await self.runtime.async_start_period()


class EndPeriodButton(PeriodStateButton):
    """End the ongoing period today."""

    _attr_translation_key = "end_period"
    _attr_icon = "mdi:stop"
    _available_when_ongoing = True

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "end_period")

    async def async_press(self) -> None:
        await self.runtime.async_end_period()


class RecordPeriodButton(MenstruationEntity, ButtonEntity):
    """Store the dates selected on the profile device."""

    _attr_translation_key = "record_period"
    _attr_icon = "mdi:content-save"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "record_period")

    async def async_press(self) -> None:
        await self.runtime.async_record(
            self.runtime.record_start, self.runtime.record_end
        )
