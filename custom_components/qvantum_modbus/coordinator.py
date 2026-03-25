"""Data update coordinator for the Qvantum Modbus integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import logging
import struct
from typing import Any

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONF_STOPBITS,
    CONNECTION_TYPE_TCP,
    DATA_TYPE_FLOAT32,
    DATA_TYPE_INT16,
    DATA_TYPE_INT32,
    DATA_TYPE_UINT16,
    DATA_TYPE_UINT32,
    DOMAIN,
    INPUT_TYPE_INPUT,
    SCAN_INTERVAL_SECONDS,
)
from .models import SENSOR_DESCRIPTIONS, ModbusSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


def _decode_registers(registers: list[int], data_type: str) -> int | float:
    """Convert raw Modbus register value(s) to the appropriate Python type.

    All 32-bit types expect two consecutive registers in big-endian word order.
    """
    if data_type == DATA_TYPE_INT16:
        # Reinterpret unsigned 16-bit as signed 16-bit
        (raw_value,) = struct.unpack(">h", struct.pack(">H", registers[0]))
        return int(raw_value)
    if data_type == DATA_TYPE_UINT16:
        return registers[0]
    if data_type in (DATA_TYPE_INT32, DATA_TYPE_UINT32, DATA_TYPE_FLOAT32):
        if len(registers) < 2:
            raise ValueError(f"Need 2 registers for {data_type}, got {len(registers)}")
        raw = (registers[0] << 16) | registers[1]
        if data_type == DATA_TYPE_INT32:
            (raw_value,) = struct.unpack(">i", struct.pack(">I", raw))
            return int(raw_value)
        if data_type == DATA_TYPE_UINT32:
            return raw
        # FLOAT32
        (raw_value,) = struct.unpack(">f", struct.pack(">I", raw))
        return float(raw_value)
    raise ValueError(f"Unsupported data_type: {data_type!r}")


def _register_count(data_type: str) -> int:
    """Return how many 16-bit registers a data type occupies."""
    if data_type in (DATA_TYPE_INT32, DATA_TYPE_UINT32, DATA_TYPE_FLOAT32):
        return 2
    return 1


class QvantumModbusCoordinator(DataUpdateCoordinator[dict[str, float | None]]):
    """Coordinator that polls a Modbus device for all defined sensors."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialise the coordinator and create the appropriate Modbus client."""
        self._base_update_interval = timedelta(seconds=SCAN_INTERVAL_SECONDS)
        self._consecutive_failures: int = 0
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=self._base_update_interval,
            config_entry=config_entry,
        )
        self._client = self._build_client(config_entry.data)
        self._device_id: int = config_entry.data[CONF_UNIT_ID]

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive update failures."""
        return self._consecutive_failures

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_client(
        data: Mapping[str, Any],
    ) -> AsyncModbusTcpClient | AsyncModbusSerialClient:
        """Instantiate the correct Modbus transport from config entry data."""
        if data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP:
            return AsyncModbusTcpClient(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
            )
        return AsyncModbusSerialClient(
            port=data[CONF_PORT],
            baudrate=data[CONF_BAUDRATE],
            bytesize=data[CONF_BYTESIZE],
            parity=data[CONF_PARITY],
            stopbits=data[CONF_STOPBITS],
        )

    async def _read_sensor(self, desc: ModbusSensorEntityDescription) -> float | None:
        """Read a single sensor register and decode the value.

        Returns None if the device returns an error response or the register
        cannot be decoded — the entity will become unavailable in that case.
        ConnectionException is intentionally NOT caught here; the caller
        converts it to UpdateFailed so the coordinator fails loudly.
        """
        count = _register_count(desc.data_type)
        try:
            if desc.input_type == INPUT_TYPE_INPUT:
                result = await self._client.read_input_registers(
                    address=desc.address,
                    count=count,
                    device_id=self._device_id,
                )
            else:
                result = await self._client.read_holding_registers(
                    address=desc.address,
                    count=count,
                    device_id=self._device_id,
                )
        except ConnectionException:
            # Let connection errors propagate — handled in _async_update_data
            raise
        except ModbusException as err:
            _LOGGER.warning(
                "Modbus protocol error reading %s (address %d): %s",
                desc.key,
                desc.address,
                err,
            )
            return None

        if result.isError():
            _LOGGER.warning(
                "Device returned error response for %s (address %d): %s",
                desc.key,
                desc.address,
                result,
            )
            return None

        if not result.registers:
            _LOGGER.warning(
                "Empty register data for %s (address %d)", desc.key, desc.address
            )
            return None

        raw = _decode_registers(result.registers, desc.data_type)
        value = round(raw * desc.scale, desc.precision)
        _LOGGER.debug(
            "Read %s (address %d): raw=%s → %s %s",
            desc.key,
            desc.address,
            raw,
            value,
            desc.native_unit_of_measurement,
        )
        return value

    def _apply_backoff(self) -> None:
        """Double the update interval on failure, capped at 32× the base."""
        self._consecutive_failures += 1
        new_interval = min(
            self._base_update_interval * (2**self._consecutive_failures),
            self._base_update_interval * 32,
        )
        self.update_interval = new_interval
        _LOGGER.debug(
            "Connection failed (attempt %d); retrying in %s",
            self._consecutive_failures,
            new_interval,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def async_disconnect(self) -> None:
        """Close the Modbus transport; called on entry unload."""
        self._client.close()

    # ------------------------------------------------------------------
    # DataUpdateCoordinator interface
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, float | None]:
        """Fetch all sensor values from the Modbus device."""
        # Explicitly connect on first call (transport is None at startup).
        # On subsequent calls, pymodbus 3.11's execute() reconnects automatically
        # if the transport dropped, so we only check here to give an early,
        # clear UpdateFailed instead of an implicit ConnectionException.
        if not self._client.connected:
            if not await self._client.connect():
                self._apply_backoff()
                raise UpdateFailed(
                    "Could not establish Modbus connection",
                    translation_domain=DOMAIN,
                    translation_key="cannot_connect",
                )

        data: dict[str, float | None] = {}
        try:
            for desc in SENSOR_DESCRIPTIONS:
                data[desc.key] = await self._read_sensor(desc)
        except ConnectionException as err:
            self._apply_backoff()
            raise UpdateFailed(
                f"Modbus connection lost during poll: {err}",
                translation_domain=DOMAIN,
                translation_key="connection_lost",
                translation_placeholders={"error": str(err)},
            ) from err

        # Success — reset backoff so the next failure starts from the base interval
        if self._consecutive_failures > 0:
            self._consecutive_failures = 0
            self.update_interval = self._base_update_interval

        return data
