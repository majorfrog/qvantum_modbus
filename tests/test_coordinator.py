"""Coordinator tests — covers coordinator.py for Silver test-coverage requirement."""

from __future__ import annotations

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
    client.read_input_registers = AsyncMock(return_value=mock_register_result())
    client.read_holding_registers = AsyncMock(return_value=mock_register_result())
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
