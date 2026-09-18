"""Constants for the Salda/MCB Modbus TCP integration."""
from __future__ import annotations

DOMAIN = "salda_mcb_modbus"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 15  # seconds

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
