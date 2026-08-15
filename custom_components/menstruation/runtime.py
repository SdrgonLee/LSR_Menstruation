"""Runtime state and local persistence."""

from __future__ import annotations

from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

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
from .model import Forecast, PeriodRecord, forecast


class MenstruationRuntime:
    """Shared runtime data for one profile."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.records: list[PeriodRecord] = []
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

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.records = sorted(
            (PeriodRecord.from_dict(item) for item in data.get("records", [])),
            key=lambda item: item.start,
        )

    async def async_record(self, start: date, end: date | None) -> None:
        self.records = [record for record in self.records if record.start != start]
        self.records.append(PeriodRecord(start, end))
        self.records.sort(key=lambda item: item.start)
        await self._save_and_notify()

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
