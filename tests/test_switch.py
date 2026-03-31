"""Switch platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN

from .fixtures import mock_error_result, mock_register_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity_id(hass: HomeAssistant, entry_id: str, key: str) -> str | None:
    """Look up entity_id via unique_id."""
    return er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{entry_id}_{key}")


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_switch_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """unit_on_off switch entity is registered after integration setup."""
    assert _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off") is not None


# ---------------------------------------------------------------------------
# is_on
# ---------------------------------------------------------------------------


async def test_switch_is_on_when_register_nonzero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """Switch reports ON when the holding register is non-zero."""
    # mock_register_result returns 215 by default — non-zero → is_on = True
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_switch_is_off_when_register_zero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_tcp_client: MagicMock,
) -> None:
    """Switch reports OFF when the holding register is 0."""
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
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


# ---------------------------------------------------------------------------
# async_turn_on / async_turn_off
# ---------------------------------------------------------------------------


async def test_switch_turn_on_writes_one(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration: MagicMock,
) -> None:
    """Turning on writes 1 to the register."""
    mock_client = setup_integration
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None

    mock_client.write_register.reset_mock()
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    mock_client.write_register.assert_called_once()
    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == 1


async def test_switch_turn_off_writes_zero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration: MagicMock,
) -> None:
    """Turning off writes 0 to the register."""
    mock_client = setup_integration
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None

    mock_client.write_register.reset_mock()
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    mock_client.write_register.assert_called_once()
    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == 0


async def test_switch_turn_on_raises_on_write_error(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration: MagicMock,
) -> None:
    """Turn on raises HomeAssistantError when the device returns a write error."""
    mock_client = setup_integration
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None

    mock_client.write_register.return_value = mock_error_result()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": entity_id}, blocking=True
        )


# ---------------------------------------------------------------------------
# available — register returns error
# ---------------------------------------------------------------------------


async def test_switch_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_tcp_client: MagicMock,
) -> None:
    """Switch is unavailable when the register read fails."""
    mock_tcp_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.write_register = AsyncMock(return_value=mock_error_result())
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
