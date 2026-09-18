"""The Salda/MCB Modbus TCP integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADDRESS_OFFSET,
    CONF_FRAMING,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_ADDRESS_OFFSET,
    DEFAULT_FRAMING,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import SaldaModbusCoordinator
from .modbus_hub import SaldaModbusHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]


def _merged(entry: ConfigEntry, key: str, default):
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave_id = entry.data[CONF_SLAVE_ID]
    framing = _merged(entry, CONF_FRAMING, DEFAULT_FRAMING)
    address_offset = _merged(entry, CONF_ADDRESS_OFFSET, DEFAULT_ADDRESS_OFFSET)
    scan_interval = _merged(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = SaldaModbusHub(host, port, slave_id, framing=framing, address_offset=address_offset)
    connected = await hub.async_connect()
    if not connected:
        _LOGGER.warning(
            "Initial connection to %s:%s (framing=%s) failed, will retry on next update",
            host, port, framing,
        )

    coordinator = SaldaModbusCoordinator(hass, hub, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SaldaModbusCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.hub.async_close()
    return unload_ok
