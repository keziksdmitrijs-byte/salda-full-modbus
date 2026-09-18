"""Select platform: writable Holding Registers with enumerated options."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LEVEL_USER, MANUFACTURER, MODEL
from .coordinator import SaldaModbusCoordinator
from .registers import SELECT_REGISTERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: SaldaModbusCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [SaldaHoldingRegisterSelect(coordinator, entry.entry_id, reg) for reg in SELECT_REGISTERS]
    async_add_entities(entities)


class SaldaHoldingRegisterSelect(CoordinatorEntity[SaldaModbusCoordinator], SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id, reg) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._options_map: dict[int, str] = reg["options"]
        self._reverse_map: dict[str, int] = {v: k for k, v in reg["options"].items()}
        self._attr_unique_id = f"{entry_id}_hr_select_{reg['address']}"
        self._attr_name = reg["name"] or reg["key"]
        self._attr_options = list(self._options_map.values())
        if reg["level"] != LEVEL_USER:
            self._attr_entity_category = SelectEntityCategory.CONFIG
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
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        raw = data.get("holding", {}).get(self._reg["address"])
        if raw is None:
            return None
        return self._options_map.get(raw)

    async def async_select_option(self, option: str) -> None:
        raw = self._reverse_map.get(option)
        if raw is None:
            raise ValueError(f"Unknown option '{option}' for {self._reg['name']}")
        ok = await self.coordinator.hub.write_holding_register(self._reg["address"], raw)
        if not ok:
            raise RuntimeError(
                f"Failed to write option '{option}' to holding register "
                f"{self._reg['address']} ({self._reg['name']})"
            )
        await self.coordinator.async_request_refresh()
