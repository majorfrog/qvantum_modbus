"""Binary sensor platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN

from .fixtures import mock_error_result, mock_register_result


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_binary_sensor_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """relay_l1 binary sensor entity is registered after integration setup."""
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
    setup_integration,
) -> None:
    """relay_l1 is ON when the register value is non-zero."""
    # mock_register_result returns 215 by default — non-zero → ON
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
    mock_tcp_client: MagicMock,
) -> None:
    """relay_l1 is OFF when the register value is zero."""
    # Return 0 for all registers → relay OFF
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_tcp_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_tcp_client.write_register = AsyncMock(
        return_value=mock_register_result(value=0)
    )
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

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
    mock_tcp_client: MagicMock,
) -> None:
    """heating_demand reports ON when its bit is set in the shared register."""
    # heating_demand checks bit 0; register value 1 → bit 0 = 1 → ON
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_tcp_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_tcp_client.write_register = AsyncMock(
        return_value=mock_register_result(value=1)
    )
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

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
    mock_tcp_client: MagicMock,
) -> None:
    """Binary sensor is unavailable when the register read fails."""
    mock_tcp_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.write_register = AsyncMock(return_value=mock_error_result())
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

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
