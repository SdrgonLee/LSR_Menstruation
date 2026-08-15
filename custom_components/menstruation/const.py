"""Constants for Menstruation."""

DOMAIN = "menstruation"
PLATFORMS = ["sensor", "binary_sensor", "calendar"]

CONF_PROFILE_NAME = "profile_name"
CONF_CYCLE_LENGTH = "cycle_length"
CONF_PERIOD_LENGTH = "period_length"
CONF_LUTEAL_PHASE = "luteal_phase"

DEFAULT_CYCLE_LENGTH = 28
DEFAULT_PERIOD_LENGTH = 5
DEFAULT_LUTEAL_PHASE = 14

SERVICE_RECORD_PERIOD = "record_period"
SERVICE_DELETE_PERIOD = "delete_period"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"

STORAGE_VERSION = 1
SIGNAL_UPDATE = f"{DOMAIN}_update"
