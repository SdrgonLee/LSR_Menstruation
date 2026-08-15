"""Menstruation sensor entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import MenstruationEntity
from .model import effective_cycle_length
from .runtime import MenstruationRuntime


@dataclass(frozen=True, kw_only=True)
class MenstruationSensorDescription(SensorEntityDescription):
    """Describe a calculated sensor."""

    value_fn: Callable[[MenstruationRuntime, date], date | int | None]


DESCRIPTIONS = (
    MenstruationSensorDescription(
        key="next_period",
        translation_key="next_period",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda runtime, today: runtime.forecast(today).next_period,
    ),
    MenstruationSensorDescription(
        key="ovulation",
        translation_key="ovulation",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda runtime, today: runtime.forecast(today).ovulation,
    ),
    MenstruationSensorDescription(
        key="fertile_start",
        translation_key="fertile_start",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda runtime, today: runtime.forecast(today).fertile_start,
    ),
    MenstruationSensorDescription(
        key="fertile_end",
        translation_key="fertile_end",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda runtime, today: runtime.forecast(today).fertile_end,
    ),
    MenstruationSensorDescription(
        key="average_cycle_length",
        translation_key="average_cycle_length",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda runtime, today: effective_cycle_length(
            runtime.records, runtime.cycle_length
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[MenstruationRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        MenstruationSensor(entry.runtime_data, description)
        for description in DESCRIPTIONS
    )


class MenstruationSensor(MenstruationEntity, SensorEntity):
    """A calculated date or duration sensor."""

    entity_description: MenstruationSensorDescription

    def __init__(
        self, runtime: MenstruationRuntime, description: MenstruationSensorDescription
    ) -> None:
        super().__init__(runtime, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> date | int | None:
        return self.entity_description.value_fn(self.runtime, dt_util.now().date())

    @property
    def extra_state_attributes(self) -> dict:
        if self.entity_description.key != "next_period":
            return {}
        prediction = self.runtime.forecast(dt_util.now().date())
        return {
            "predicted_end": prediction.next_period_end,
            "records_used": len(self.runtime.records),
            "medical_disclaimer": "Calendar estimate only; not medical advice or contraception.",
        }
