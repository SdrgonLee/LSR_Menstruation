"""Read-only calendars compatible with Home Assistant calendar cards."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import MenstruationEntity
from .model import (
    effective_cycle_length,
    iter_fertile_segments,
    iter_fertile_windows,
    iter_predicted_periods,
)
from .runtime import MenstruationRuntime


EVENT_TEXTS = {
    "en": {
        "recorded_period": ("Period", "Recorded period"),
        "predicted_period": (
            "Predicted period",
            "Calendar-based estimate; not medical advice.",
        ),
        "fertile_window": (
            "Fertile window",
            "Calendar-based estimate; not contraception or medical advice.",
        ),
        "ovulation": (
            "Ovulation",
            "Calendar-based estimate; not medical advice.",
        ),
    },
    "ko": {
        "recorded_period": ("생리", "기록된 생리 기간"),
        "predicted_period": (
            "생리 예상",
            "달력 기반 추정치이며 의료적 판단에 사용할 수 없습니다.",
        ),
        "fertile_window": (
            "가임기",
            "달력 기반 추정치이며 피임이나 의료적 판단에 사용할 수 없습니다.",
        ),
        "ovulation": (
            "배란일",
            "달력 기반 추정치이며 의료적 판단에 사용할 수 없습니다.",
        ),
    },
}


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
            OvulationCalendar(entry.runtime_data),
        ]
    )


class MenstruationCalendar(MenstruationEntity, CalendarEntity):
    """Base read-only all-day calendar."""

    def __init__(self, runtime: MenstruationRuntime, key: str) -> None:
        super().__init__(runtime, key)

    def _events(self) -> Iterable[CalendarEvent]:
        raise NotImplementedError

    def _event_text(self, key: str) -> tuple[str, str]:
        """Return event text in the Home Assistant system language."""
        language = (
            self.runtime.hass.config.language.replace("_", "-").split("-", 1)[0]
        )
        texts = EVENT_TEXTS.get(language, EVENT_TEXTS["en"])
        return texts[key]

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

    @callback
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
        summary, description = self._event_text("recorded_period")
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
                summary=summary,
                description=description,
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
        summary, description = self._event_text("predicted_period")
        for start, inclusive_end in iter_predicted_periods(
            self.runtime.records, cycle, self.runtime.period_length
        ):
            yield CalendarEvent(
                start=start,
                end=inclusive_end + timedelta(days=1),
                summary=summary,
                description=description,
            )


class FertilityCalendar(MenstruationCalendar):
    """Calendar containing estimated fertile windows."""

    _attr_translation_key = "fertility"
    _attr_icon = "mdi:sprout"
    _attr_initial_color = "#66BB6A"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "fertility")

    def _events(self) -> Iterable[CalendarEvent]:
        cycle = effective_cycle_length(self.runtime.records, self.runtime.cycle_length)
        fertile_summary, fertile_description = self._event_text("fertile_window")
        for start, inclusive_end, ovulation in iter_fertile_windows(
            self.runtime.records, cycle, self.runtime.luteal_phase
        ):
            for segment_start, segment_end in iter_fertile_segments(
                start, inclusive_end, ovulation
            ):
                yield CalendarEvent(
                    start=segment_start,
                    end=segment_end + timedelta(days=1),
                    summary=fertile_summary,
                    description=fertile_description,
                )


class OvulationCalendar(MenstruationCalendar):
    """Calendar containing estimated ovulation days."""

    _attr_translation_key = "ovulation"
    _attr_icon = "mdi:circle-double"
    _attr_initial_color = "#2E7D32"

    def __init__(self, runtime: MenstruationRuntime) -> None:
        super().__init__(runtime, "ovulation_calendar")

    def _events(self) -> Iterable[CalendarEvent]:
        cycle = effective_cycle_length(self.runtime.records, self.runtime.cycle_length)
        summary, description = self._event_text("ovulation")
        for _, _, ovulation in iter_fertile_windows(
            self.runtime.records, cycle, self.runtime.luteal_phase
        ):
            yield CalendarEvent(
                start=ovulation,
                end=ovulation + timedelta(days=1),
                summary=summary,
                description=description,
            )
