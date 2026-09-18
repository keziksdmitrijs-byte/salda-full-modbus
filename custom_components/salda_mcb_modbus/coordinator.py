"""DataUpdateCoordinator for the Salda/MCB Modbus TCP integration.

Polls all registers used by the enabled entity platforms in batched Modbus
requests (contiguous ranges, capped at MAX_BATCH) to keep TCP round trips low.
Read failures are recorded per range; if every range fails, UpdateFailed is
raised so Home Assistant shows the integration/entities as unavailable and
logs a clear communication error.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .modbus_hub import SaldaModbusHub
from .registers import (
    BINARY_SENSOR_REGISTERS,
    NUMBER_REGISTERS,
    SELECT_REGISTERS,
    SENSOR_REGISTERS,
    SWITCH_REGISTERS,
)

_LOGGER = logging.getLogger(__name__)

MAX_BATCH = 100


def _build_ranges(addresses):
    if not addresses:
        return []
    addresses = sorted(set(addresses))
    ranges = []
    start = addresses[0]
    prev = addresses[0]
    count = 1
    for addr in addresses[1:]:
        if addr == prev + 1 and count < MAX_BATCH:
            count += 1
            prev = addr
            continue
        ranges.append((start, count))
        start = addr
        prev = addr
        count = 1
    ranges.append((start, count))
    return ranges


class SaldaModbusCoordinator(DataUpdateCoordinator):
    """Coordinates all Modbus polling for one AHU/controller."""

    def __init__(self, hass: HomeAssistant, hub: SaldaModbusHub, scan_interval: int) -> None:
        super().__init__(
            hass, _LOGGER, name="salda_mcb_modbus",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.hub = hub
        self._hr_addresses = sorted(
            {e["address"] for e in NUMBER_REGISTERS} | {e["address"] for e in SELECT_REGISTERS}
        )
        self._coil_addresses = sorted({e["address"] for e in SWITCH_REGISTERS})
        self._di_addresses = sorted({e["address"] for e in BINARY_SENSOR_REGISTERS})
        self._ir_addresses = sorted({e["address"] for e in SENSOR_REGISTERS})

        self._hr_ranges = _build_ranges(self._hr_addresses)
        self._coil_ranges = _build_ranges(self._coil_addresses)
        self._di_ranges = _build_ranges(self._di_addresses)
        self._ir_ranges = _build_ranges(self._ir_addresses)

    async def _async_update_data(self) -> dict:
        holding, coils, discrete, input_regs, errors = {}, {}, {}, {}, []

        try:
            connected = await self.hub.async_connect()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Cannot connect to Modbus TCP device: {err}") from err

        if not connected:
            raise UpdateFailed("Modbus TCP connection failed")

        total_ranges = (
            len(self._hr_ranges) + len(self._coil_ranges)
            + len(self._di_ranges) + len(self._ir_ranges)
        )
        ok_ranges = 0

        for start, count in self._hr_ranges:
            values = await self.hub.read_holding_registers(start, count)
            if values is None:
                errors.append(f"HR {start}-{start + count - 1}")
                continue
            ok_ranges += 1
            for i, val in enumerate(values):
                holding[start + i] = val

        for start, count in self._coil_ranges:
            values = await self.hub.read_coils(start, count)
            if values is None:
                errors.append(f"COIL {start}-{start + count - 1}")
                continue
            ok_ranges += 1
            for i, val in enumerate(values):
                coils[start + i] = val

        for start, count in self._di_ranges:
            values = await self.hub.read_discrete_inputs(start, count)
            if values is None:
                errors.append(f"DI {start}-{start + count - 1}")
                continue
            ok_ranges += 1
            for i, val in enumerate(values):
                discrete[start + i] = val

        for start, count in self._ir_ranges:
            values = await self.hub.read_input_registers(start, count)
            if values is None:
                errors.append(f"IR {start}-{start + count - 1}")
                continue
            ok_ranges += 1
            for i, val in enumerate(values):
                input_regs[start + i] = val

        if ok_ranges == 0 and total_ranges > 0:
            raise UpdateFailed(
                "All Modbus read requests failed - check host/port/slave id "
                "and that the AHU is powered and reachable"
            )

        if errors:
            _LOGGER.warning(
                "Some Modbus ranges failed to read (%d/%d): %s",
                len(errors), total_ranges, ", ".join(errors),
            )

        return {
            "holding": holding, "coils": coils,
            "discrete_inputs": discrete, "input_registers": input_regs,
            "errors": errors,
        }
