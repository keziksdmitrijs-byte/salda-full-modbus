"""Constants for the Salda/MCB Modbus TCP integration."""
from __future__ import annotations

DOMAIN = "salda_mcb_modbus"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FRAMING = "framing"
CONF_ADDRESS_OFFSET = "address_offset"
CONF_SKIP_TEST = "skip_connection_test"

DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_FRAMING = "tcp"
DEFAULT_ADDRESS_OFFSET = 1  # 1 = send documented address as-is, 0 = subtract 1

FRAMING_TCP = "tcp"
FRAMING_RTU_OVER_TCP = "rtu_over_tcp"
FRAMING_OPTIONS = [FRAMING_TCP, FRAMING_RTU_OVER_TCP]

MANUFACTURER = "Salda"
MODEL = "MCB / miniMCB (AHU controller)"

REG_HOLDING = "holding"
REG_COIL = "coil"
REG_DISCRETE_INPUT = "discrete_input"
REG_INPUT = "input"

LEVEL_USER = "User"
LEVEL_ADJUSTER = "Adjuster"
LEVEL_SERVICE = "Service"

SIGNAL_NEW_DATA = f"{DOMAIN}_new_data"

PLATFORM_MODULES = ["sensor", "binary_sensor", "number", "select", "switch"]
