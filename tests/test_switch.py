"""Switch platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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


def _entity_id(hass: HomeAssistant, entry_id: str, key: str) -> str | None:
    """Look up entity_id via unique_id."""
    return er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{entry_id}_{key}")


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_switch_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """unit_on_off switch entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)
    assert _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off") is not None


# ---------------------------------------------------------------------------
# is_on
# ---------------------------------------------------------------------------


async def test_switch_is_on_when_register_nonzero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Switch reports ON when the holding register is non-zero."""
    # mock_register_result returns 215 by default — non-zero → is_on = True
    await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


async def test_switch_is_off_when_register_zero(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Switch reports OFF when the holding register is 0."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=0, count=kw.get("count", 1))
    )
    mock_client.write_register = AsyncMock(return_value=mock_register_result(value=0))

    await _setup(hass, mock_tcp_config_entry, mock_client)
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
) -> None:
    """Turning on writes 1 to the register."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
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
) -> None:
    """Turning off writes 0 to the register."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
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
) -> None:
    """Turn on raises HomeAssistantError when the device returns a write error."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
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
) -> None:
    """Switch is unavailable when the register read fails."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_client.write_register = AsyncMock(return_value=mock_error_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, "unit_on_off")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
