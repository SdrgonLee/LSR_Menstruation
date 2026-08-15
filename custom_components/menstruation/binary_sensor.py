"""Menstruation binary sensor entities."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import MenstruationEntity
from .model import is_period_day
from .runtime import MenstruationRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[MenstruationRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            PeriodBinarySensor(entry.runtime_data),
            FertileBinarySensor(entry.runtime_data),
        ]
    )


class PeriodBinarySensor(MenstruationEntity, BinarySensorEntity):
    """Whether today is part of a recorded period."""

    _attr_translation_key = "period"
    _attr_icon = "mdi:water"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "period")

    @property
    def is_on(self) -> bool:
        return is_period_day(
            dt_util.now().date(), self.runtime.records, self.runtime.period_length
        )


class FertileBinarySensor(MenstruationEntity, BinarySensorEntity):
    """Whether today is in the estimated fertile window."""

    _attr_translation_key = "fertile"
    _attr_icon = "mdi:sprout"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "fertile")

    @property
    def is_on(self) -> bool:
        today = dt_util.now().date()
        prediction = self.runtime.forecast(today)
        return bool(
            prediction.fertile_start
            and prediction.fertile_end
            and prediction.fertile_start <= today <= prediction.fertile_end
        )
