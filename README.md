# Menstruation for Home Assistant

A local, profile-based menstrual cycle tracker and calendar for Home Assistant.

> Predictions are simple calendar estimates. They are not medical advice and must not be used for contraception.

## Features

- Locally stores period start/end dates in Home Assistant
- Estimates the next period from up to six recent plausible cycle intervals
- Estimates ovulation and the fertile window
- Creates one Home Assistant device per profile
- Provides date sensors, binary sensors, editable record dates, a record button, and three read-only standard calendar entities
- Includes English and Korean UI translations

## Install

Copy `custom_components/menstruation` into the same path under your Home Assistant configuration directory and restart Home Assistant. Then open **Settings → Devices & services → Add integration → Menstruation**.

### HACS custom repository

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/SdrgonLee/LSR_Menstruation` as an **Integration**.
3. Download **Menstruation**, restart Home Assistant, and add it from **Settings → Devices & services**.

## Record a period

Open **Settings → Devices & services → Menstruation → your profile device**. Under the device configuration:

1. Set **Record start date**.
2. Adjust **Record end date** if needed. It follows the start date using the configured default period length.
3. Press **Record period**.

You can also use **Developer tools → Actions → Menstruation: Record period**, or call:

```yaml
action: menstruation.record_period
data:
  config_entry_id: "YOUR_PROFILE_ENTRY_ID"
  start_date: "2026-08-15"
  end_date: "2026-08-19"
```

`end_date` is optional. Calling the action again with the same `start_date` replaces that record.

## Default calendar card

The three calendars appear in Home Assistant's sidebar Calendar automatically. They also work with the built-in dashboard calendar card and third-party cards that consume standard `calendar.*` entities.

```yaml
type: calendar
title: Cycle calendar
initial_view: dayGridMonth
entities:
  - calendar.my_cycle_recorded_periods
  - calendar.my_cycle_predicted_periods
  - calendar.my_cycle_fertility_estimates
```

Actual entity IDs depend on the profile name and can be copied from the profile's device page.

## Calculation

- Cycle length: rounded mean of the last six intervals between recorded starts, ignoring intervals outside 15–60 days
- Fallback cycle: configured value (default 28 days)
- Ovulation estimate: predicted period start minus the configured luteal phase (default 14 days)
- Fertile window: five days before through one day after estimated ovulation

All records are stored under Home Assistant's `.storage` directory and are not sent externally.

## License

MIT License. See [LICENSE](LICENSE).
