"""Coordinator tests — covers coordinator.py for Silver test-coverage requirement."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ConnectionException, ModbusException
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:
    from tests.common import MockConfigEntry  # type: ignore[no-redef]

from custom_components.qvantum_modbus.const import DOMAIN, SCAN_INTERVAL_SECONDS
from custom_components.qvantum_modbus.coordinator import QvantumModbusCoordinator

from .fixtures import (
    MOCK_TCP_ENTRY_DATA,
    mock_empty_result,
    mock_error_result,
    mock_register_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and register a mock TCP config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_TCP_ENTRY_DATA,
        title="192.168.1.100:502",
        unique_id="tcp_192.168.1.100_502_1",
    )
    entry.add_to_hass(hass)
    return entry


def _make_coordinator(
    hass: HomeAssistant, mock_client: MagicMock
) -> QvantumModbusCoordinator:
    """Create a coordinator backed by mock_client (already connected)."""
    entry = _make_entry(hass)
    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        return QvantumModbusCoordinator(hass, entry)


def _connected_client() -> MagicMock:
    """Return a mock client that appears already connected."""
    client = MagicMock()
    client.connected = True
    client.connect = AsyncMock(return_value=True)
    client.close = MagicMock()
    client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )
    client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )
    client.write_register = AsyncMock(return_value=mock_register_result())
    return client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_successful_update(hass: HomeAssistant) -> None:
    """Successful poll returns decoded sensor values."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    data = await coordinator._async_update_data()

    assert data["bt1_outdoor"] == pytest.approx(21.5)
    assert coordinator._consecutive_failures == 0
    assert coordinator.update_interval == timedelta(seconds=SCAN_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Connection failure — UpdateFailed + backoff
# ---------------------------------------------------------------------------


async def test_connect_failure_raises_update_failed(hass: HomeAssistant) -> None:
    """When connect() returns False the coordinator raises UpdateFailed."""
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_connect_failure_applies_backoff(hass: HomeAssistant) -> None:
    """Each connection failure doubles the poll interval."""
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()
    coordinator = _make_coordinator(hass, mock_client)

    base = timedelta(seconds=SCAN_INTERVAL_SECONDS)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 1
    assert coordinator.update_interval == base * 2

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 2
    assert coordinator.update_interval == base * 4


async def test_backoff_capped_at_32x(hass: HomeAssistant) -> None:
    """The backoff interval is capped at 32× the base interval."""
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()
    coordinator = _make_coordinator(hass, mock_client)

    base = timedelta(seconds=SCAN_INTERVAL_SECONDS)
    for _ in range(10):  # run well past the cap
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    assert coordinator.update_interval == base * 32


async def test_backoff_resets_on_success(hass: HomeAssistant) -> None:
    """Backoff counters reset to base after a successful poll."""
    # First fail to accumulate backoff
    fail_client = MagicMock()
    fail_client.connected = False
    fail_client.connect = AsyncMock(return_value=False)
    fail_client.close = MagicMock()
    coordinator = _make_coordinator(hass, fail_client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_failures == 1

    # Now swap the client to a healthy one and verify reset
    good_client = _connected_client()
    coordinator._client = good_client

    data = await coordinator._async_update_data()

    assert data["bt1_outdoor"] == pytest.approx(21.5)
    assert coordinator._consecutive_failures == 0
    assert coordinator.update_interval == timedelta(seconds=SCAN_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# ConnectionException during poll → UpdateFailed + backoff
# ---------------------------------------------------------------------------


async def test_connection_exception_during_poll(hass: HomeAssistant) -> None:
    """ConnectionException raised mid-poll is converted to UpdateFailed with backoff."""
    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(
        side_effect=ConnectionException("lost")
    )
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(UpdateFailed, match="Modbus connection lost"):
        await coordinator._async_update_data()

    assert coordinator._consecutive_failures == 1


# ---------------------------------------------------------------------------
# ModbusException during register read → value is None, not UpdateFailed
# ---------------------------------------------------------------------------


async def test_modbus_exception_returns_none(hass: HomeAssistant) -> None:
    """A per-register ModbusException makes that value None, not a full failure."""
    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(side_effect=ModbusException("bad crc"))
    coordinator = _make_coordinator(hass, mock_client)

    data = await coordinator._async_update_data()

    assert data["bt1_outdoor"] is None
    # Coordinator itself did not fail — no backoff applied
    assert coordinator._consecutive_failures == 0


# ---------------------------------------------------------------------------
# Error response from device → value is None
# ---------------------------------------------------------------------------


async def test_error_response_returns_none(hass: HomeAssistant) -> None:
    """An error response (isError=True) from the device makes the value None."""
    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    coordinator = _make_coordinator(hass, mock_client)

    data = await coordinator._async_update_data()

    assert data["bt1_outdoor"] is None


# ---------------------------------------------------------------------------
# Empty registers → value is None
# ---------------------------------------------------------------------------


async def test_empty_registers_returns_none(hass: HomeAssistant) -> None:
    """An empty registers list makes the value None."""
    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(return_value=mock_empty_result())
    coordinator = _make_coordinator(hass, mock_client)

    data = await coordinator._async_update_data()

    assert data["bt1_outdoor"] is None


# ---------------------------------------------------------------------------
# Async disconnect
# ---------------------------------------------------------------------------


async def test_async_disconnect_closes_client(hass: HomeAssistant) -> None:
    """async_disconnect() calls close() on the Modbus client."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    coordinator.async_disconnect()

    mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# _decode_registers — 32-bit types and error cases (pure unit tests)
# ---------------------------------------------------------------------------

from custom_components.qvantum_modbus.coordinator import (  # noqa: E402
    _decode_registers,
    _register_count,
)
from custom_components.qvantum_modbus.const import (  # noqa: E402
    DATA_TYPE_FLOAT32,
    DATA_TYPE_INT32,
    DATA_TYPE_UINT16,
    DATA_TYPE_UINT32,
    INPUT_TYPE_INPUT,
)


def test_decode_registers_int32_negative() -> None:
    """0xFFFF_FFFF decodes to -1 for INT32."""
    assert _decode_registers([0xFFFF, 0xFFFF], DATA_TYPE_INT32) == -1


def test_decode_registers_int32_positive() -> None:
    """Positive INT32 value decodes correctly."""
    assert _decode_registers([0x0001, 0x0001], DATA_TYPE_INT32) == 0x00010001


def test_decode_registers_uint32() -> None:
    """UINT32 value decodes to the combined raw integer."""
    assert _decode_registers([0x0001, 0x0000], DATA_TYPE_UINT32) == 0x00010000


def test_decode_registers_float32() -> None:
    """0x3F80_0000 decodes to 1.0 for FLOAT32."""
    import math

    result = _decode_registers([0x3F80, 0x0000], DATA_TYPE_FLOAT32)
    assert math.isclose(float(result), 1.0)


def test_decode_registers_32bit_requires_two_registers() -> None:
    """Passing one register for a 32-bit type raises ValueError."""
    with pytest.raises(ValueError, match="Need 2 registers"):
        _decode_registers([100], DATA_TYPE_INT32)


def test_decode_registers_unsupported_type_raises() -> None:
    """Unsupported data_type raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported data_type"):
        _decode_registers([100], "bad_type")


# ---------------------------------------------------------------------------
# _register_count — 32-bit types return 2
# ---------------------------------------------------------------------------


def test_register_count_32bit_returns_2() -> None:
    """INT32, UINT32, and FLOAT32 each occupy two registers."""
    assert _register_count(DATA_TYPE_INT32) == 2
    assert _register_count(DATA_TYPE_UINT32) == 2
    assert _register_count(DATA_TYPE_FLOAT32) == 2


# ---------------------------------------------------------------------------
# _get_enabled_keys — cache hit
# ---------------------------------------------------------------------------


async def test_get_enabled_keys_cache_hit(hass: HomeAssistant) -> None:
    """Second call to _async_update_data hits the cached enabled-keys set."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    await coordinator._async_update_data()
    assert coordinator._enabled_keys is not None
    first_keys = coordinator._enabled_keys

    # Second call — same object is returned (early-return cache hit)
    await coordinator._async_update_data()
    assert coordinator._enabled_keys is first_keys


# ---------------------------------------------------------------------------
# _read_batched — empty request list
# ---------------------------------------------------------------------------


async def test_read_batched_empty_requests(hass: HomeAssistant) -> None:
    """Calling _read_batched with an empty list returns an empty dict immediately."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    result = await coordinator._read_batched([])

    assert result == {}


# ---------------------------------------------------------------------------
# _read_register_int — success and error paths
# ---------------------------------------------------------------------------


async def test_read_register_int_success(hass: HomeAssistant) -> None:
    """_read_register_int returns the decoded integer value on a successful read."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    result = await coordinator._read_register_int(
        "test_key", 100, DATA_TYPE_UINT16, INPUT_TYPE_INPUT
    )

    assert isinstance(result, int)


async def test_read_register_int_returns_none_on_error(hass: HomeAssistant) -> None:
    """_read_register_int returns None when the device returns a Modbus error."""
    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(
        side_effect=ModbusException("register error")
    )
    coordinator = _make_coordinator(hass, mock_client)

    result = await coordinator._read_register_int(
        "test_key", 100, DATA_TYPE_UINT16, INPUT_TYPE_INPUT
    )

    assert result is None


# ---------------------------------------------------------------------------
# write_holding_register — bounds, reconnect, negative value, write error
# ---------------------------------------------------------------------------


async def test_write_register_below_min_raises(hass: HomeAssistant) -> None:
    """write_holding_register raises HomeAssistantError when value < min_raw."""
    from homeassistant.exceptions import HomeAssistantError

    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(HomeAssistantError):
        await coordinator.write_holding_register(100, 5, min_raw=10)


async def test_write_register_above_max_raises(hass: HomeAssistant) -> None:
    """write_holding_register raises HomeAssistantError when value > max_raw."""
    from homeassistant.exceptions import HomeAssistantError

    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(HomeAssistantError):
        await coordinator.write_holding_register(100, 100, max_raw=50)


async def test_write_register_reconnect_fails_raises(hass: HomeAssistant) -> None:
    """write_holding_register raises HomeAssistantError when reconnect fails."""
    from homeassistant.exceptions import HomeAssistantError

    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(HomeAssistantError):
        await coordinator.write_holding_register(100, 42)


async def test_write_register_negative_value_twos_complement(
    hass: HomeAssistant,
) -> None:
    """Negative values are converted to unsigned 16-bit two's complement before writing."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)

    await coordinator.write_holding_register(100, -1)

    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == 0xFFFF  # -1 & 0xFFFF


async def test_write_register_device_error_raises(hass: HomeAssistant) -> None:
    """write_holding_register raises HomeAssistantError when device returns an error."""
    from homeassistant.exceptions import HomeAssistantError

    mock_client = _connected_client()
    mock_client.write_register = AsyncMock(return_value=mock_error_result())
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(HomeAssistantError):
        await coordinator.write_holding_register(100, 42)


# ---------------------------------------------------------------------------
# _async_update_data — combined sensor skipped + empty _read_batched call
# ---------------------------------------------------------------------------


async def test_combined_sensors_skipped_when_not_enabled(hass: HomeAssistant) -> None:
    """With _enabled_keys=set(), the combined-sensor loop executes 'continue'."""
    mock_client = _connected_client()
    coordinator = _make_coordinator(hass, mock_client)
    coordinator._enabled_keys = set()  # Nothing enabled

    data = await coordinator._async_update_data()

    assert data == {}


# ---------------------------------------------------------------------------
# CancelledError propagation through a wrapped ModbusException
# ---------------------------------------------------------------------------


async def test_cancelled_error_wrapped_in_modbus_exception_propagates(
    hass: HomeAssistant,
) -> None:
    """pymodbus-wrapped CancelledError is unwrapped, transport closed, and re-raised."""
    cancelled = asyncio.CancelledError()
    exc = ModbusException("wrapped cancel")
    exc.__cause__ = cancelled

    mock_client = _connected_client()
    mock_client.read_input_registers = AsyncMock(side_effect=exc)
    coordinator = _make_coordinator(hass, mock_client)

    with pytest.raises(asyncio.CancelledError):
        await coordinator._async_update_data()

    mock_client.close.assert_called()
