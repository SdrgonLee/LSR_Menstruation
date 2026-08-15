"""Data model and cycle calculations independent from Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class PeriodRecord:
    """A recorded menstrual period."""

    start: date
    end: date | None = None
    ongoing: bool = False

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "ongoing": self.ongoing,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PeriodRecord":
        return cls(
            date.fromisoformat(value["start"]),
            date.fromisoformat(value["end"]) if value.get("end") else None,
            bool(value.get("ongoing", False)),
        )


@dataclass(frozen=True, slots=True)
class Forecast:
    """The current or next calculated dates."""

    cycle_length: int
    next_period: date | None
    next_period_end: date | None
    ovulation: date | None
    fertile_start: date | None
    fertile_end: date | None


def validate_period_record(start: date, end: date | None, today: date) -> None:
    """Validate one recorded period range."""
    if start > today:
        raise ValueError("Start date cannot be in the future")
    if end is not None and end < start:
        raise ValueError("End date cannot be before start date")
    if end is not None and (end - start).days >= 15:
        raise ValueError("A recorded period cannot exceed 15 days")


def effective_cycle_length(records: list[PeriodRecord], fallback: int) -> int:
    """Use the last six plausible recorded intervals."""
    starts = sorted({record.start for record in records})
    intervals = [
        (later - earlier).days
        for earlier, later in zip(starts, starts[1:], strict=False)
        if 15 <= (later - earlier).days <= 60
    ]
    return round(mean(intervals[-6:])) if intervals else fallback


def forecast(
    records: list[PeriodRecord],
    fallback_cycle: int,
    period_length: int,
    luteal_phase: int,
    today: date,
) -> Forecast:
    """Calculate the current/upcoming period and fertile window."""
    cycle = effective_cycle_length(records, fallback_cycle)
    if not records:
        return Forecast(cycle, None, None, None, None, None)

    last_start = max(record.start for record in records)
    period_start = last_start + timedelta(days=cycle)
    while period_start + timedelta(days=period_length) <= today:
        period_start += timedelta(days=cycle)

    fertile_ovulation = period_start - timedelta(days=luteal_phase)
    fertile_start = fertile_ovulation - timedelta(days=5)
    fertile_end = fertile_ovulation + timedelta(days=1)
    while fertile_end < today:
        fertile_ovulation += timedelta(days=cycle)
        fertile_start += timedelta(days=cycle)
        fertile_end += timedelta(days=cycle)

    return Forecast(
        cycle,
        period_start,
        period_start + timedelta(days=period_length - 1),
        fertile_ovulation,
        fertile_start,
        fertile_end,
    )


def is_period_day(today: date, records: list[PeriodRecord], period_length: int) -> bool:
    """Return whether today is in an explicitly recorded period."""
    for record in records:
        if record.ongoing and record.start <= today:
            return True
        end = record.end or record.start + timedelta(days=period_length - 1)
        if record.start <= today <= end:
            return True
    return False


def iter_predicted_periods(
    records: list[PeriodRecord], cycle_length: int, period_length: int, limit: int = 60
) -> Iterator[tuple[date, date]]:
    """Yield predicted period ranges after the latest record."""
    if not records:
        return
    start = max(record.start for record in records) + timedelta(days=cycle_length)
    for _ in range(limit):
        yield start, start + timedelta(days=period_length - 1)
        start += timedelta(days=cycle_length)


def iter_fertile_windows(
    records: list[PeriodRecord], cycle_length: int, luteal_phase: int, limit: int = 60
) -> Iterator[tuple[date, date, date]]:
    """Yield fertile start, fertile end, and ovulation dates."""
    for period_start, _ in iter_predicted_periods(records, cycle_length, 1, limit):
        ovulation = period_start - timedelta(days=luteal_phase)
        yield ovulation - timedelta(days=5), ovulation + timedelta(days=1), ovulation


def iter_fertile_segments(
    start: date, inclusive_end: date, ovulation: date
) -> Iterator[tuple[date, date]]:
    """Yield fertile-window ranges excluding the ovulation day."""
    before_end = ovulation - timedelta(days=1)
    if start <= before_end:
        yield start, min(before_end, inclusive_end)

    after_start = ovulation + timedelta(days=1)
    if after_start <= inclusive_end:
        yield max(after_start, start), inclusive_end
