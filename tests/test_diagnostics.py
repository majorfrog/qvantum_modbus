"""Diagnostics platform tests."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.qvantum_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .fixtures import MOCK_PORT, MOCK_UNIT_ID


# ---------------------------------------------------------------------------
# async_get_config_entry_diagnostics
# ---------------------------------------------------------------------------


async def test_diagnostics_contains_entry_data(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """Diagnostics output includes the config entry data with sensitive fields redacted."""
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "entry_data" in result
    entry_data = result["entry_data"]
    # Host is redacted for privacy
    assert entry_data["host"] == "**REDACTED**"
    assert entry_data["port"] == MOCK_PORT
    assert entry_data["unit_id"] == MOCK_UNIT_ID


async def test_diagnostics_contains_coordinator_stats(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """Diagnostics output includes coordinator update stats."""
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
    setup_integration,
) -> None:
    """Diagnostics output includes device-level fields (serial, FW, IP)."""
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
    setup_integration,
) -> None:
    """Diagnostics output includes the full data snapshot."""
    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)

    assert "data" in result
    # bt1_outdoor should be present after a successful poll
    assert "bt1_outdoor" in result["data"]


async def test_diagnostics_data_none_coordinator(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """Diagnostics handles coordinator.data being None without raising."""
    # Force coordinator.data to None after setup
    coordinator = mock_tcp_config_entry.runtime_data
    coordinator.data = None

    result = await async_get_config_entry_diagnostics(hass, mock_tcp_config_entry)
    assert result["data"] == {}
    assert result["device"]["serial_number"] is None
