"""Sensor platform: read-only measured values from Input Registers."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LEVEL_USER, MANUFACTURER, MODEL
from .coordinator import SaldaModbusCoordinator
from .registers import SENSOR_REGISTERS

_LOGGER = logging.getLogger(__name__)

UNIT_MAP = {"°C": "°C", "%": "%", "ppm": "ppm", "Pa": "Pa", "RPM": "rpm", "rpm": "rpm", "V": "V"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SaldaModbusCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SaldaInputRegisterSensor(coordinator, entry.entry_id, reg) for reg in SENSOR_REGISTERS]
    async_add_entities(entities)


class SaldaInputRegisterSensor(CoordinatorEntity[SaldaModbusCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, reg) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry_id}_ir_{reg['address']}"
        self._attr_name = reg["name"] or reg["key"]
        unit = UNIT_MAP.get(reg["unit"], reg["unit"] or None)
        self._attr_native_unit_of_measurement = unit if unit else None
        if reg["level"] != LEVEL_USER:
            self._attr_entity_category = SensorEntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)}, manufacturer=MANUFACTURER, model=MODEL, name="Salda AHU"
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return self._reg["address"] in data.get("input_registers", {})

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw = data.get("input_registers", {}).get(self._reg["address"])
        if raw is None:
            return None
        scale = self._reg["scale"]
        value = raw * scale
        if scale != 1:
            value = round(value, 2)
        return value
