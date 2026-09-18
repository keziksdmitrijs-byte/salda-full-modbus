"""Modbus TCP hub wrapping pymodbus for the Salda/MCB AHU controller.

All register addresses in the vendor documentation are 1-based. pymodbus (and the
Modbus protocol itself) addresses registers starting at 0, so every read/write in
this hub subtracts 1 from the documented address. If your controller firmware
turns out to expect the documented address literally, flip ADDRESS_OFFSET to 0.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

ADDRESS_OFFSET = 1  # documented address -> wire address correction


@dataclass
class ModbusReadResult:
    holding: dict
    coils: dict
    discrete_inputs: dict
    input_registers: dict
    errors: list


class SaldaModbusHub:
    """Thin async wrapper around pymodbus AsyncModbusTcpClient."""

    def __init__(self, host: str, port: int, slave_id: int) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._client: AsyncModbusTcpClient | None = None

    async def async_connect(self) -> bool:
        if self._client is None:
            self._client = AsyncModbusTcpClient(self._host, port=self._port)
        if not self._client.connected:
            await self._client.connect()
        return self._client.connected

    async def async_close(self) -> None:
        if self._client is not None:
            self._client.close()

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    async def _ensure_connected(self) -> None:
        if not self.connected:
            ok = await self.async_connect()
            if not ok:
                raise ConnectionError(
                    f"Unable to connect to Modbus TCP device at {self._host}:{self._port}"
                )

    async def read_holding_registers(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.read_holding_registers(
                wire_addr, count=count, slave=self._slave_id
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading HR %s: %s", address, err)
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading HR %s: %s", address, resp)
            return None
        return [_to_signed16(v) for v in resp.registers]

    async def read_input_registers(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.read_input_registers(
                wire_addr, count=count, slave=self._slave_id
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading IR %s: %s", address, err)
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading IR %s: %s", address, resp)
            return None
        return [_to_signed16(v) for v in resp.registers]

    async def read_coils(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.read_coils(
                wire_addr, count=count, slave=self._slave_id
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading Coil %s: %s", address, err)
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading Coil %s: %s", address, resp)
            return None
        return list(resp.bits[:count])

    async def read_discrete_inputs(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.read_discrete_inputs(
                wire_addr, count=count, slave=self._slave_id
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading DI %s: %s", address, err)
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading DI %s: %s", address, resp)
            return None
        return list(resp.bits[:count])

    async def write_holding_register(self, address: int, value: int) -> bool:
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.write_register(
                wire_addr, _to_unsigned16(value), slave=self._slave_id
            )
        except ModbusException as err:
            _LOGGER.error("Modbus exception writing HR %s=%s: %s", address, value, err)
            return False
        if resp is None or resp.isError():
            _LOGGER.error("Error response writing HR %s=%s: %s", address, value, resp)
            return False
        return True

    async def write_coil(self, address: int, value: bool) -> bool:
        await self._ensure_connected()
        wire_addr = address - ADDRESS_OFFSET
        try:
            resp = await self._client.write_coil(wire_addr, value, slave=self._slave_id)
        except ModbusException as err:
            _LOGGER.error("Modbus exception writing Coil %s=%s: %s", address, value, err)
            return False
        if resp is None or resp.isError():
            _LOGGER.error("Error response writing Coil %s=%s: %s", address, value, resp)
            return False
        return True


def _to_signed16(value: int) -> int:
    if value >= 0x8000:
        return value - 0x10000
    return value


def _to_unsigned16(value: int) -> int:
    if value < 0:
        return value + 0x10000
    return value
