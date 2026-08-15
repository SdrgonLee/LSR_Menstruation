"""Editable dates for recording a period from the device page."""

from datetime import date

from homeassistant.components.date import DateEntity
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
    """Set up period record date inputs."""
    async_add_entities(
        [
            RecordStartDate(entry.runtime_data),
            RecordEndDate(entry.runtime_data),
        ]
    )


class RecordStartDate(MenstruationEntity, DateEntity):
    """Start date used by the record-period button."""

    _attr_translation_key = "record_start"
    _attr_icon = "mdi:calendar-start"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "record_start")

    @property
    def native_value(self) -> date:
        return self.runtime.record_start

    async def async_set_value(self, value: date) -> None:
        self.runtime.set_record_start(value)


class RecordEndDate(MenstruationEntity, DateEntity):
    """End date used by the record-period button."""

    _attr_translation_key = "record_end"
    _attr_icon = "mdi:calendar-end"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "record_end")

    @property
    def native_value(self) -> date:
        return self.runtime.record_end

    async def async_set_value(self, value: date) -> None:
        self.runtime.set_record_end(value)
