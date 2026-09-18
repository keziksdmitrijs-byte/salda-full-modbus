"""Modbus hub wrapping pymodbus for the Salda/MCB AHU controller.

Supports Modbus TCP and RTU-over-TCP framing, a configurable address offset
(documented-as-is vs strict 0-based), and both pymodbus keyword conventions
("slave" pre-3.10, "device_id" from 3.10 onward).
"""
from __future__ import annotations

import logging

import pymodbus
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)


def _pymodbus_device_kwarg_name() -> str:
    try:
        raw_version = getattr(pymodbus, "__version__", "0.0.0")
        parts = raw_version.split(".")[:2]
        major, minor = int(parts[0]), int(parts[1])
        if (major, minor) >= (3, 10):
            return "device_id"
    except (ValueError, IndexError, AttributeError):
        _LOGGER.debug("Could not parse pymodbus version %s, defaulting to 'slave'", pymodbus)
    return "slave"


_DEVICE_KW = _pymodbus_device_kwarg_name()


def _get_rtu_framer():
    try:
        from pymodbus import FramerType

        return FramerType.RTU
    except ImportError:
        try:
            from pymodbus.framer import FramerType

            return FramerType.RTU
        except ImportError:
            _LOGGER.warning(
                "This pymodbus version has no FramerType.RTU; falling back to "
                "plain Modbus TCP framing"
            )
            return None


class SaldaModbusHub:
    """Thin async wrapper around pymodbus AsyncModbusTcpClient."""

    def __init__(
        self,
        host: str,
        port: int,
        slave_id: int,
        framing: str = "tcp",
        address_offset: int = 1,
    ) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._framing = framing
        self._address_offset = address_offset
        self._client: AsyncModbusTcpClient | None = None

    def _device_kwargs(self) -> dict:
        return {_DEVICE_KW: self._slave_id}

    def _make_client(self) -> AsyncModbusTcpClient:
        kwargs = {"host": self._host, "port": self._port}
        if self._framing == "rtu_over_tcp":
            framer = _get_rtu_framer()
            if framer is not None:
                kwargs["framer"] = framer
        return AsyncModbusTcpClient(**kwargs)

    async def async_connect(self) -> bool:
        if self._client is None:
            self._client = self._make_client()
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
                    f"Unable to connect to Modbus device at {self._host}:{self._port} "
                    f"(framing={self._framing})"
                )

    def _wire_address(self, address: int) -> int:
        return address - self._address_offset

    async def read_holding_registers(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.read_holding_registers(
                wire_addr, count=count, **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading HR %s: %s", address, err)
            return None
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch reading HR %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading HR %s: %s", address, resp)
            return None
        return [_to_signed16(v) for v in resp.registers]

    async def read_input_registers(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.read_input_registers(
                wire_addr, count=count, **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading IR %s: %s", address, err)
            return None
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch reading IR %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading IR %s: %s", address, resp)
            return None
        return [_to_signed16(v) for v in resp.registers]

    async def read_coils(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.read_coils(
                wire_addr, count=count, **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading Coil %s: %s", address, err)
            return None
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch reading Coil %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading Coil %s: %s", address, resp)
            return None
        return list(resp.bits[:count])

    async def read_discrete_inputs(self, address: int, count: int = 1):
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.read_discrete_inputs(
                wire_addr, count=count, **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.debug("Modbus exception reading DI %s: %s", address, err)
            return None
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch reading DI %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
            return None
        if resp is None or resp.isError():
            _LOGGER.debug("Error response reading DI %s: %s", address, resp)
            return None
        return list(resp.bits[:count])

    async def write_holding_register(self, address: int, value: int) -> bool:
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.write_register(
                wire_addr, _to_unsigned16(value), **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.error("Modbus exception writing HR %s=%s: %s", address, value, err)
            return False
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch writing HR %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
            return False
        if resp is None or resp.isError():
            _LOGGER.error("Error response writing HR %s=%s: %s", address, value, resp)
            return False
        return True

    async def write_coil(self, address: int, value: bool) -> bool:
        await self._ensure_connected()
        wire_addr = self._wire_address(address)
        try:
            resp = await self._client.write_coil(
                wire_addr, value, **self._device_kwargs()
            )
        except ModbusException as err:
            _LOGGER.error("Modbus exception writing Coil %s=%s: %s", address, value, err)
            return False
        except TypeError as err:
            _LOGGER.error(
                "pymodbus API mismatch writing Coil %s (keyword '%s'): %s",
                address, _DEVICE_KW, err,
            )
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
