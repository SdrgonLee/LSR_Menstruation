"""Tests for cycle calculations without requiring Home Assistant."""

from datetime import date
import importlib.util
from pathlib import Path
import sys
import unittest

MODEL_PATH = Path(__file__).parents[1] / "custom_components" / "menstruation" / "model.py"
SPEC = importlib.util.spec_from_file_location("menstruation_model", MODEL_PATH)
assert SPEC and SPEC.loader
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)

PeriodRecord = MODEL.PeriodRecord
effective_cycle_length = MODEL.effective_cycle_length
forecast = MODEL.forecast
is_period_day = MODEL.is_period_day
iter_fertile_windows = MODEL.iter_fertile_windows
iter_fertile_segments = MODEL.iter_fertile_segments
iter_predicted_periods = MODEL.iter_predicted_periods
validate_period_record = MODEL.validate_period_record


class CycleCalculationTests(unittest.TestCase):
    """Verify prediction and calendar boundaries."""

    def test_fallback_with_one_record(self) -> None:
        result = forecast(
            [PeriodRecord(date(2026, 7, 1))], 28, 5, 14, date(2026, 7, 10)
        )
        self.assertEqual(result.cycle_length, 28)
        self.assertEqual(result.next_period, date(2026, 7, 29))
        self.assertEqual(result.next_period_end, date(2026, 8, 2))
        self.assertEqual(result.ovulation, date(2026, 7, 15))
        self.assertEqual(result.fertile_start, date(2026, 7, 10))
        self.assertEqual(result.fertile_end, date(2026, 7, 16))

    def test_recent_average_ignores_implausible_interval(self) -> None:
        records = [
            PeriodRecord(date(2026, 1, 1)),
            PeriodRecord(date(2026, 1, 29)),
            PeriodRecord(date(2026, 2, 26)),
            PeriodRecord(date(2026, 5, 1)),  # 64 days: ignored
            PeriodRecord(date(2026, 5, 30)),
        ]
        self.assertEqual(effective_cycle_length(records, 30), 28)

    def test_forecast_advances_past_missed_cycles(self) -> None:
        result = forecast(
            [PeriodRecord(date(2026, 1, 1))], 28, 5, 14, date(2026, 3, 1)
        )
        self.assertEqual(result.next_period, date(2026, 2, 26))
        self.assertEqual(result.next_period_end, date(2026, 3, 2))
        self.assertEqual(result.fertile_start, date(2026, 3, 7))
        self.assertEqual(result.ovulation, date(2026, 3, 12))

    def test_recorded_period_uses_explicit_or_default_end(self) -> None:
        self.assertTrue(
            is_period_day(date(2026, 8, 5), [PeriodRecord(date(2026, 8, 1))], 5)
        )
        self.assertFalse(
            is_period_day(date(2026, 8, 6), [PeriodRecord(date(2026, 8, 1))], 5)
        )
        self.assertTrue(
            is_period_day(
                date(2026, 8, 7),
                [PeriodRecord(date(2026, 8, 1), date(2026, 8, 7))],
                5,
            )
        )

    def test_ongoing_period_persists_and_remains_active(self) -> None:
        record = PeriodRecord(date(2026, 8, 1), ongoing=True)
        restored = PeriodRecord.from_dict(record.to_dict())
        self.assertEqual(restored, record)
        self.assertTrue(is_period_day(date(2026, 8, 15), [restored], 5))
        self.assertFalse(is_period_day(date(2026, 7, 31), [restored], 5))

    def test_old_record_storage_defaults_to_not_ongoing(self) -> None:
        restored = PeriodRecord.from_dict(
            {"start": "2026-08-01", "end": None}
        )
        self.assertFalse(restored.ongoing)

    def test_calendar_generators(self) -> None:
        records = [PeriodRecord(date(2026, 8, 1))]
        self.assertEqual(
            next(iter_predicted_periods(records, 28, 5)),
            (date(2026, 8, 29), date(2026, 9, 2)),
        )
        self.assertEqual(
            next(iter_fertile_windows(records, 28, 14)),
            (date(2026, 8, 10), date(2026, 8, 16), date(2026, 8, 15)),
        )
        self.assertEqual(
            list(
                iter_fertile_segments(
                    date(2026, 8, 10), date(2026, 8, 16), date(2026, 8, 15)
                )
            ),
            [
                (date(2026, 8, 10), date(2026, 8, 14)),
                (date(2026, 8, 16), date(2026, 8, 16)),
            ],
        )

    def test_no_records_has_no_dates(self) -> None:
        result = forecast([], 28, 5, 14, date(2026, 8, 15))
        self.assertIsNone(result.next_period)
        self.assertEqual(list(iter_predicted_periods([], 28, 5)), [])

    def test_period_record_validation(self) -> None:
        today = date(2026, 8, 15)
        validate_period_record(date(2026, 8, 11), date(2026, 8, 15), today)
        with self.assertRaisesRegex(ValueError, "future"):
            validate_period_record(date(2026, 8, 16), None, today)
        with self.assertRaisesRegex(ValueError, "before"):
            validate_period_record(date(2026, 8, 11), date(2026, 8, 10), today)
        with self.assertRaisesRegex(ValueError, "15 days"):
            validate_period_record(date(2026, 8, 1), date(2026, 8, 16), today)


if __name__ == "__main__":
    unittest.main()
