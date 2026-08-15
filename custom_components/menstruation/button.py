"""Button for recording a period from the device page."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import MenstruationEntity
from .runtime import MenstruationRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[MenstruationRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the period record button."""
    async_add_entities([RecordPeriodButton(entry.runtime_data)])


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
