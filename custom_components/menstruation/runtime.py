"""Runtime state and local persistence."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CYCLE_LENGTH,
    CONF_LUTEAL_PHASE,
    CONF_PERIOD_LENGTH,
    DEFAULT_CYCLE_LENGTH,
    DEFAULT_LUTEAL_PHASE,
    DEFAULT_PERIOD_LENGTH,
    SIGNAL_UPDATE,
    STORAGE_VERSION,
)
from .model import Forecast, PeriodRecord, forecast, validate_period_record


class MenstruationRuntime:
    """Shared runtime data for one profile."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.records: list[PeriodRecord] = []
        today = dt_util.now().date()
        self.record_start = today
        self.record_end = today + timedelta(days=self.period_length - 1)
        self._store: Store[dict] = Store(
            hass, STORAGE_VERSION, f"menstruation.{entry.entry_id}"
        )

    @property
    def settings(self) -> dict:
        return {**self.entry.data, **self.entry.options}

    @property
    def cycle_length(self) -> int:
        return int(self.settings.get(CONF_CYCLE_LENGTH, DEFAULT_CYCLE_LENGTH))

    @property
    def period_length(self) -> int:
        return int(self.settings.get(CONF_PERIOD_LENGTH, DEFAULT_PERIOD_LENGTH))

    @property
    def luteal_phase(self) -> int:
        return int(self.settings.get(CONF_LUTEAL_PHASE, DEFAULT_LUTEAL_PHASE))

    def forecast(self, today: date) -> Forecast:
        return forecast(
            self.records,
            self.cycle_length,
            self.period_length,
            self.luteal_phase,
            today,
        )

    @property
    def ongoing_record(self) -> PeriodRecord | None:
        """Return the active period record, if one exists."""
        ongoing = [record for record in self.records if record.ongoing]
        return max(ongoing, key=lambda item: item.start) if ongoing else None

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.records = sorted(
            (PeriodRecord.from_dict(item) for item in data.get("records", [])),
            key=lambda item: item.start,
        )

    async def async_record(self, start: date, end: date | None) -> None:
        try:
            validate_period_record(start, end, dt_util.now().date())
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        self.records = [record for record in self.records if record.start != start]
        self.records.append(PeriodRecord(start, end))
        self.records.sort(key=lambda item: item.start)
        await self._save_and_notify()

    async def async_start_period(self) -> None:
        """Start an ongoing period today."""
        if self.ongoing_record is not None:
            raise ServiceValidationError("A period is already in progress")
        today = dt_util.now().date()
        self.records = [record for record in self.records if record.start != today]
        self.records.append(PeriodRecord(today, ongoing=True))
        self.records.sort(key=lambda item: item.start)
        await self._save_and_notify()

    async def async_end_period(self) -> None:
        """End the ongoing period today."""
        ongoing = self.ongoing_record
        if ongoing is None:
            raise ServiceValidationError("No period is currently in progress")
        today = dt_util.now().date()
        self.records = [record for record in self.records if record is not ongoing]
        self.records.append(PeriodRecord(ongoing.start, today))
        self.records.sort(key=lambda item: item.start)
        await self._save_and_notify()

    def set_record_start(self, value: date) -> None:
        """Update the record form start and keep its current duration."""
        if value > dt_util.now().date():
            raise ServiceValidationError("Start date cannot be in the future")
        duration = (self.record_end - self.record_start).days
        if not 0 <= duration < 15:
            duration = self.period_length - 1
        self.record_start = value
        self.record_end = value + timedelta(days=duration)
        async_dispatcher_send(self.hass, self.signal)

    def set_record_end(self, value: date) -> None:
        """Update the record form end date."""
        try:
            validate_period_record(
                self.record_start, value, dt_util.now().date()
            )
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        self.record_end = value
        async_dispatcher_send(self.hass, self.signal)

    async def async_delete(self, start: date) -> bool:
        new_records = [record for record in self.records if record.start != start]
        if len(new_records) == len(self.records):
            return False
        self.records = new_records
        await self._save_and_notify()
        return True

    async def _save_and_notify(self) -> None:
        await self._store.async_save(
            {"records": [record.to_dict() for record in self.records]}
        )
        async_dispatcher_send(self.hass, self.signal)

    @property
    def signal(self) -> str:
        return f"{SIGNAL_UPDATE}_{self.entry.entry_id}"
