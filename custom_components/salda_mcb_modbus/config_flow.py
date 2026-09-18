"""Config flow for the Salda/MCB Modbus TCP integration.

Mirrors the "Connection parameters of the recuperator's Modbus TCP
interface" form: host, TCP port, a slave/unit id slider, a Modbus framing
dropdown (plain TCP vs RTU-over-TCP for RS-485 gateways), an address-offset
choice (1 = send documented address as-is, 0 = strict 0-based), a polling
interval, and an "Add without connection test" checkbox for units that only
answer some registers and would otherwise fail the probe.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ADDRESS_OFFSET,
    CONF_FRAMING,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SKIP_TEST,
    CONF_SLAVE_ID,
    DEFAULT_ADDRESS_OFFSET,
    DEFAULT_FRAMING,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    FRAMING_OPTIONS,
    FRAMING_RTU_OVER_TCP,
    FRAMING_TCP,
)
from .modbus_hub import SaldaModbusHub

_LOGGER = logging.getLogger(__name__)

FRAMING_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            {"value": FRAMING_TCP, "label": "Modbus TCP"},
            {"value": FRAMING_RTU_OVER_TCP, "label": "Modbus RTU over TCP (RS-485 gateway)"},
        ],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="framing",
    )
)


def _build_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
            vol.Required(
                CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=247)),
            vol.Required(
                CONF_FRAMING, default=defaults.get(CONF_FRAMING, DEFAULT_FRAMING)
            ): FRAMING_SELECTOR,
            vol.Required(
                CONF_ADDRESS_OFFSET,
                default=defaults.get(CONF_ADDRESS_OFFSET, DEFAULT_ADDRESS_OFFSET),
            ): vol.All(vol.Coerce(int), vol.In([1, 0])),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
            vol.Optional(
                CONF_SKIP_TEST, default=defaults.get(CONF_SKIP_TEST, False)
            ): cv.boolean,
        }
    )


async def _async_validate_connection(
    host: str, port: int, slave_id: int, framing: str, address_offset: int
) -> str | None:
    """Try to open a connection and read one register.

    Returns an error key (for translations) or None on success. The real
    exception is always logged with full detail so the HA log shows exactly
    what failed instead of a generic message.
    """
    hub = SaldaModbusHub(host, port, slave_id, framing=framing, address_offset=address_offset)
    try:
        connected = await hub.async_connect()
        if not connected:
            _LOGGER.error(
                "Could not open a Modbus socket to %s:%s (slave id %s, framing %s)",
                host, port, slave_id, framing,
            )
            return "cannot_connect"
        result = await hub.read_holding_registers(1, 1)
        if result is None:
            _LOGGER.error(
                "Connected to %s:%s but reading holding register 1 (slave id %s, "
                "framing %s, address_offset %s) returned no data - see preceding "
                "log lines for the pymodbus error. If this unit only answers some "
                "registers, use 'Add without connection test'.",
                host, port, slave_id, framing, address_offset,
            )
            return "cannot_connect"
    except ConnectionError as err:
        _LOGGER.error("Connection error validating Salda Modbus connection: %s", err)
        return "cannot_connect"
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception(
            "Unexpected error validating Salda Modbus connection to %s:%s: %s",
            host, port, err,
        )
        return "unknown"
    finally:
        await hub.async_close()
    return None


class SaldaModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = (
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE_ID]}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            if user_input.get(CONF_SKIP_TEST):
                return self.async_create_entry(
                    title=f"Salda AHU ({user_input[CONF_HOST]})", data=user_input
                )

            error = await _async_validate_connection(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_SLAVE_ID],
                user_input[CONF_FRAMING],
                user_input[CONF_ADDRESS_OFFSET],
            )
            if error is None:
                return self.async_create_entry(
                    title=f"Salda AHU ({user_input[CONF_HOST]})", data=user_input
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}),
            errors=errors,
            description_placeholders={
                "info": "Connection parameters of the recuperator's Modbus TCP interface."
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "SaldaModbusOptionsFlow":
        return SaldaModbusOptionsFlow(config_entry)


class SaldaModbusOptionsFlow(config_entries.OptionsFlow):
    """Options flow to adjust connection parameters after setup, without
    removing and re-adding the integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_build_schema(current))
