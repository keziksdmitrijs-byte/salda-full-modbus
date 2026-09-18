"""Switch platform: writable Coils (boolean commands/toggles)."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LEVEL_USER, MANUFACTURER, MODEL
from .coordinator import SaldaModbusCoordinator
from .registers import SWITCH_REGISTERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SaldaModbusCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SaldaCoilSwitch(coordinator, entry.entry_id, reg) for reg in SWITCH_REGISTERS]
    async_add_entities(entities)


class SaldaCoilSwitch(CoordinatorEntity[SaldaModbusCoordinator], SwitchEntity):
    """A read/write Coil exposed as a HA switch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, reg) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry_id}_coil_{reg['address']}"
        self._attr_name = reg["name"] or reg["key"]
        if reg["level"] != LEVEL_USER:
            self._attr_entity_category = SwitchEntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)}, manufacturer=MANUFACTURER, model=MODEL, name="Salda AHU"
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return self._reg["address"] in data.get("coils", {})

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        return data.get("coils", {}).get(self._reg["address"])

    async def async_turn_on(self, **kwargs) -> None:
        ok = await self.coordinator.hub.write_coil(self._reg["address"], True)
        if not ok:
            raise RuntimeError(f"Failed to turn on coil {self._reg['address']} ({self._reg['name']})")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        ok = await self.coordinator.hub.write_coil(self._reg["address"], False)
        if not ok:
            raise RuntimeError(f"Failed to turn off coil {self._reg['address']} ({self._reg['name']})")
        await self.coordinator.async_request_refresh()
