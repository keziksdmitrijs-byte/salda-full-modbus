"""Binary sensor platform: Discrete Inputs (statuses and alarms)."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityCategory,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LEVEL_USER, MANUFACTURER, MODEL
from .coordinator import SaldaModbusCoordinator
from .registers import BINARY_SENSOR_REGISTERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SaldaModbusCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        SaldaDiscreteInputBinarySensor(coordinator, entry.entry_id, reg)
        for reg in BINARY_SENSOR_REGISTERS
    ]
    async_add_entities(entities)


class SaldaDiscreteInputBinarySensor(CoordinatorEntity[SaldaModbusCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, reg) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_unique_id = f"{entry_id}_di_{reg['address']}"
        self._attr_name = reg["name"] or reg["key"]
        if reg["is_alarm"]:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            self._attr_entity_category = BinarySensorEntityCategory.DIAGNOSTIC
        elif reg["level"] != LEVEL_USER:
            self._attr_entity_category = BinarySensorEntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)}, manufacturer=MANUFACTURER, model=MODEL, name="Salda AHU"
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data or {}
        return self._reg["address"] in data.get("discrete_inputs", {})

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        return data.get("discrete_inputs", {}).get(self._reg["address"])
