"""Sensor platform tests — covers sensor.py and __init__.py for Silver test-coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from custom_components.qvantum_modbus.const import DOMAIN

from .fixtures import MOCK_BT1_VALUE, mock_register_result


# ---------------------------------------------------------------------------
# Integration setup helpers
# ---------------------------------------------------------------------------


async def _setup(
    hass: HomeAssistant, mock_tcp_config_entry, mock_client: MagicMock | None = None
) -> MagicMock:
    """Set up the integration and return the active mock client."""
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.close = MagicMock()
        mock_client.read_input_registers = AsyncMock(
            return_value=mock_register_result()
        )

    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        mock_tcp_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_client


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_sensor_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    entity_registry: EntityRegistry,
) -> None:
    """BT1 temperature sensor entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)

    # Look up by domain + unique_id instead; unique_id is deterministic
    entry = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_qvantum_bt1",
    )
    assert entry is not None


# ---------------------------------------------------------------------------
# native_value — happy path
# ---------------------------------------------------------------------------


async def test_sensor_native_value(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """BT1 sensor reports the decoded register value."""
    await _setup(hass, mock_tcp_config_entry)

    # Find the sensor state — entity_id may vary by title; check via unique_id
    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_qvantum_bt1",
    )
    assert entry is not None
    state = hass.states.get(entry)
    assert state is not None
    assert float(state.state) == pytest.approx(MOCK_BT1_VALUE)


# ---------------------------------------------------------------------------
# available — coordinator data is None
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_coordinator_fails(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Sensor is unavailable when coordinator raises UpdateFailed on first refresh."""
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()

    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        mock_tcp_config_entry.add_to_hass(hass)
        # async_config_entry_first_refresh raises ConfigEntryNotReady on failure,
        # so the entry fails to set up — that is the expected behaviour.
        await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.config_entries import ConfigEntryState

    assert mock_tcp_config_entry.state == ConfigEntryState.SETUP_RETRY, (
        "Entry should be in SETUP_RETRY after first-refresh failure"
    )


# ---------------------------------------------------------------------------
# available — register value is None
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Sensor is unavailable when the register value is None (e.g. protocol error)."""
    from .fixtures import mock_error_result

    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    # Error result → coordinator returns {key: None}
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)

    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_qvantum_bt1",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# async_setup_entry / async_unload_entry
# ---------------------------------------------------------------------------


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Integration sets up and unloads cleanly."""
    from homeassistant.config_entries import ConfigEntryState

    mock_client = await _setup(hass, mock_tcp_config_entry)

    assert mock_tcp_config_entry.state == ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_tcp_config_entry.state == ConfigEntryState.NOT_LOADED
    mock_client.close.assert_called_once()
