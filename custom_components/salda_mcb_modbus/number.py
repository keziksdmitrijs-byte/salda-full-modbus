"""Number platform: writable Holding Registers with a numeric range."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberEntityCategory, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LEVEL_USER, MANUFACTURER, MODEL
from .coordinator import SaldaModbusCoordinator
from .registers import NUMBER_REGISTERS

_LOGGER = logging.getLogger(__name__)

UNIT_MAP = {"°C": "°C", "%": "%", "ppm": "ppm", "Pa": "Pa", "s": "s", "min": "min", "h": "h"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SaldaModbusCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SaldaHoldingRegisterNumber(coordinator, entry.entry_id, reg) for reg in NUMBER_REGISTERS]
    async_add_entities(entities)


class SaldaHoldingRegisterNumber(CoordinatorEntity[SaldaModbusCoordinator], NumberEntity):
    """A read/write Holding Register exposed as a HA number (slider)."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, entry_id, reg) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry_id}_hr_number_{reg['address']}"
        self._attr_name = reg["name"] or reg["key"]
        self._attr_native_min_value = reg["min"]
        self._attr_native_max_value = reg["max"]
        self._attr_native_step = reg["step"] if reg["step"] else 1
        unit = UNIT_MAP.get(reg["unit"], reg["unit"] or None)
        self._attr_native_unit_of_measurement = unit if unit else None
        if reg["level"] != LEVEL_USER:
            self._attr_entity_category = NumberEntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)}, manufacturer=MANUFACTURER, model=MODEL, name="Salda AHU"
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return self._reg["address"] in data.get("holding", {})

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw = data.get("holding", {}).get(self._reg["address"])
        if raw is None:
            return None
        scale = self._reg["scale"]
        value = raw * scale
        if scale != 1:
            value = round(value, 2)
        return value

    async def async_set_native_value(self, value: float) -> None:
        scale = self._reg["scale"] or 1
        raw = int(round(value / scale))
        ok = await self.coordinator.hub.write_holding_register(self._reg["address"], raw)
        if not ok:
            raise RuntimeError(
                f"Failed to write {value} to holding register {self._reg['address']} "
                f"({self._reg['name']})"
            )
        await self.coordinator.async_request_refresh()
