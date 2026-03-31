"""Binary sensor platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN

from .fixtures import mock_error_result, mock_register_result


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
# Entity creation
# ---------------------------------------------------------------------------


async def test_binary_sensor_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """relay_l1 binary sensor entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_relay_l1",
    )
    assert entry is not None


# ---------------------------------------------------------------------------
# is_on — whole-register sensor
# ---------------------------------------------------------------------------


async def test_binary_sensor_is_on_when_register_is_nonzero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """relay_l1 is ON when the register value is non-zero."""
    # mock_register_result returns 215 by default — non-zero → ON
    await _setup(hass, mock_tcp_config_entry)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_relay_l1",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_binary_sensor_is_off_when_register_is_zero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """relay_l1 is OFF when the register value is zero."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    # Return 0 for all registers → relay OFF
    mock_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_client.write_register = AsyncMock(return_value=mock_register_result(value=0))

    await _setup(hass, mock_tcp_config_entry, mock_client)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_relay_l1",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


# ---------------------------------------------------------------------------
# is_on — bitmask sensor (heating_demand uses bit 0 of a shared register)
# ---------------------------------------------------------------------------


async def test_binary_sensor_bitmask_is_on(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """heating_demand reports ON when its bit is set in the shared register."""
    # heating_demand checks bit 0; register value 1 → bit 0 = 1 → ON
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_client.write_register = AsyncMock(return_value=mock_register_result(value=1))

    await _setup(hass, mock_tcp_config_entry, mock_client)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_heating_demand",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


# ---------------------------------------------------------------------------
# available — register returns error
# ---------------------------------------------------------------------------


async def test_binary_sensor_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Binary sensor is unavailable when the register read fails."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_client.write_register = AsyncMock(return_value=mock_error_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "binary_sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_relay_l1",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
