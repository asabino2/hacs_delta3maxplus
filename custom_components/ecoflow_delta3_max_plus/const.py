"""Constants for the EcoFlow Delta 3 Max Plus integration."""

from datetime import timedelta

DOMAIN = "ecoflow_delta3_max_plus"

CONF_ACCESS_KEY = "access_key"
CONF_SECRET_KEY = "secret_key"
CONF_SELECTED_SNS = "selected_sns"
CONF_SELECTED_DEVICES = "selected_devices"
CONF_SCAN_INTERVAL_MODE = "scan_interval_mode"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"

SCAN_INTERVAL_MODE_DEFAULT = "default"
SCAN_INTERVAL_MODE_CUSTOM = "custom"

DATA_API = "api"
DATA_COORDINATOR = "coordinator"
DATA_DEVICES = "devices"

ATTR_DESCRIPTION = "description"
ATTR_DEVICE_SN = "device_sn"

SERVICE_TURN_OFF_AC1 = "turn_off_ac1"
SERVICE_TURN_OFF_AC2 = "turn_off_ac2"
SERVICE_TURN_ON_AC1 = "turn_on_ac1"
SERVICE_TURN_ON_AC2 = "turn_on_ac2"
SERVICE_TURN_OFF_ALL_AC = "turn_off_all_ac"
SERVICE_TURN_ON_ALL_AC = "turn_on_all_ac"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

API_HOSTS = ("api-e.ecoflow.com", "api-a.ecoflow.com")
DEVICE_LIST_ENDPOINT_CANDIDATES = (
    ("/device/list", {"page": 1, "size": 100}),
    ("/device/list", {"pageNum": 1, "pageSize": 100}),
    ("/device/all", {}),
)
