"""Read-only calendars compatible with Home Assistant calendar cards."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import MenstruationEntity
from .model import effective_cycle_length, iter_fertile_windows, iter_predicted_periods
from .runtime import MenstruationRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[MenstruationRuntime],
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            RecordedPeriodCalendar(entry.runtime_data),
            PredictedPeriodCalendar(entry.runtime_data),
            FertilityCalendar(entry.runtime_data),
        ]
    )


class MenstruationCalendar(MenstruationEntity, CalendarEntity):
    """Base read-only all-day calendar."""

    def __init__(self, runtime: MenstruationRuntime, key: str) -> None:
        super().__init__(runtime, key)

    def _events(self) -> Iterable[CalendarEvent]:
        raise NotImplementedError

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        upcoming = [event for event in self._events() if event.end > today]
        return min(upcoming, key=lambda item: item.start) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        lower = start_date.date()
        upper = end_date.date()
        return sorted(
            (
                event
                for event in self._events()
                if event.start < upper and event.end > lower
            ),
            key=lambda item: item.start,
        )

    def _handle_update(self) -> None:
        super()._handle_update()
        self.async_update_event_listeners()


class RecordedPeriodCalendar(MenstruationCalendar):
    """Calendar containing user-recorded periods."""

    _attr_translation_key = "recorded_periods"
    _attr_icon = "mdi:calendar-heart"
    _attr_initial_color = "#D81B60"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "recorded_periods")

    def _events(self) -> Iterable[CalendarEvent]:
        for record in self.runtime.records:
            if record.ongoing:
                inclusive_end = max(dt_util.now().date(), record.start)
            else:
                inclusive_end = record.end or record.start + timedelta(
                    days=self.runtime.period_length - 1
                )
            yield CalendarEvent(
                start=record.start,
                end=inclusive_end + timedelta(days=1),
                summary="Menstruation",
                description="Recorded period",
            )


class PredictedPeriodCalendar(MenstruationCalendar):
    """Calendar containing calculated future periods."""

    _attr_translation_key = "predicted_periods"
    _attr_icon = "mdi:calendar-clock"
    _attr_initial_color = "#F06292"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "predicted_periods")

    def _events(self) -> Iterable[CalendarEvent]:
        cycle = effective_cycle_length(self.runtime.records, self.runtime.cycle_length)
        for start, inclusive_end in iter_predicted_periods(
            self.runtime.records, cycle, self.runtime.period_length
        ):
            yield CalendarEvent(
                start=start,
                end=inclusive_end + timedelta(days=1),
                summary="Predicted menstruation",
                description="Calendar-based estimate; not medical advice.",
            )


class FertilityCalendar(MenstruationCalendar):
    """Calendar containing estimated fertile windows and ovulation days."""

    _attr_translation_key = "fertility"
    _attr_icon = "mdi:sprout"
    _attr_initial_color = "#43A047"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "fertility")

    def _events(self) -> Iterable[CalendarEvent]:
        cycle = effective_cycle_length(self.runtime.records, self.runtime.cycle_length)
        for start, inclusive_end, ovulation in iter_fertile_windows(
            self.runtime.records, cycle, self.runtime.luteal_phase
        ):
            yield CalendarEvent(
                start=start,
                end=inclusive_end + timedelta(days=1),
                summary="Estimated fertile window",
                description="Calendar-based estimate; not contraception or medical advice.",
            )
            yield CalendarEvent(
                start=ovulation,
                end=ovulation + timedelta(days=1),
                summary="Estimated ovulation",
                description="Calendar-based estimate; not medical advice.",
            )
