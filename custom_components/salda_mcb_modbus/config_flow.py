"""Config flow for the Salda/MCB Modbus TCP integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_SLAVE_ID,
    DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SLAVE_ID, DOMAIN,
)
from .modbus_hub import SaldaModbusHub

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
    }
)


async def _async_validate_connection(hass, host, port, slave_id):
    hub = SaldaModbusHub(host, port, slave_id)
    try:
        connected = await hub.async_connect()
        if not connected:
            return "cannot_connect"
        result = await hub.read_holding_registers(1, 1)
        if result is None:
            return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error validating Salda Modbus connection")
        return "unknown"
    finally:
        await hub.async_close()
    return None


class SaldaModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            error = await _async_validate_connection(
                self.hass, user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_SLAVE_ID]
            )
            if error is None:
                return self.async_create_entry(
                    title=f"Salda AHU ({user_input[CONF_HOST]})", data=user_input
                )
            errors["base"] = error

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return SaldaModbusOptionsFlow(config_entry)


class SaldaModbusOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
