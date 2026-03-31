"""Diagnostics platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.qvantum_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .fixtures import MOCK_HOST, MOCK_PORT, MOCK_UNIT_ID, mock_register_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_client: MagicMock | None = None,
) -> MagicMock:
    """Set up the integration and return the active mock client."""
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.close = MagicMock()
        mock_client.read_input_registers = AsyncMock(
            side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
        )
        mock_client.read_holding_registers = AsyncMock(
            side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
        )
        mock_client.write_register = AsyncMock(return_value=mock_register_result())

    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        mock_tcp_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_client


# ---------------------------------------------------------------------------
# async_get_config_entry_diagnostics
# ---------------------------------------------------------------------------


async def test_diagnostics_contains_entry_data(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Diagnostics output includes the config entry data."""
    await _setup(hass, mock_tcp_config_entry)
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "entry_data" in result
    entry_data = result["entry_data"]
    assert entry_data["host"] == MOCK_HOST
    assert entry_data["port"] == MOCK_PORT
    assert entry_data["unit_id"] == MOCK_UNIT_ID


async def test_diagnostics_contains_coordinator_stats(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Diagnostics output includes coordinator update stats."""
    await _setup(hass, mock_tcp_config_entry)
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "coordinator" in result
    coordinator = result["coordinator"]
    assert "update_interval" in coordinator
    assert "last_update_success" in coordinator
    assert "consecutive_failures" in coordinator
    assert coordinator["last_update_success"] is True
    assert coordinator["consecutive_failures"] == 0


async def test_diagnostics_contains_device_info(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Diagnostics output includes device-level fields (serial, FW, IP)."""
    await _setup(hass, mock_tcp_config_entry)
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "device" in result
    device = result["device"]
    # Keys must be present even if values are None / not yet decoded
    assert "serial_number" in device
    assert "fw_version" in device
    assert "ip_address" in device


async def test_diagnostics_contains_register_data(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Diagnostics output includes the full data snapshot."""
    await _setup(hass, mock_tcp_config_entry)
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "data" in result
    # bt1_outdoor should be present after a successful poll
    assert "bt1_outdoor" in result["data"]


async def test_diagnostics_data_none_coordinator(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Diagnostics handles coordinator.data being None without raising."""
    from unittest.mock import PropertyMock

    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )
    mock_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )
    mock_client.write_register = AsyncMock(return_value=mock_register_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)

    # Force coordinator.data to None after setup
    coordinator = mock_tcp_config_entry.runtime_data
    coordinator.data = None

    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)
    assert result["data"] == {}
    assert result["device"]["serial_number"] is None
