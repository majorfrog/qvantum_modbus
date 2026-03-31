"""Select platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.models import SELECT_DESCRIPTIONS

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
    return er.async_get(hass).async_get_entity_id("select", DOMAIN, f"{entry_id}_{key}")


# Pick the first select description to use for generic tests
_FIRST_SELECT = SELECT_DESCRIPTIONS[0]


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_select_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """First select entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)
    assert (
        _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key) is not None
    )


# ---------------------------------------------------------------------------
# current_option — mapped value
# ---------------------------------------------------------------------------


async def test_select_current_option_mapped(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Select shows the mapped option for the raw register value."""
    # default mock returns 215, which may not be in the value_map;
    # use 0 which is always the first/lowest key in all our selects.
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
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    # Raw 0 should map to the first option in the value_map
    expected = _FIRST_SELECT.value_map[0]
    assert state.state == expected


# ---------------------------------------------------------------------------
# async_select_option — valid option
# ---------------------------------------------------------------------------


async def test_select_option_writes_raw_value(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Selecting a valid option writes the corresponding raw int to the register."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None

    # Pick the first valid option from the description
    raw_key, option_string = next(iter(_FIRST_SELECT.value_map.items()))

    mock_client.write_register.reset_mock()
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": option_string},
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_client.write_register.assert_called_once()
    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == raw_key


# ---------------------------------------------------------------------------
# async_select_option — write error propagates
# ---------------------------------------------------------------------------


async def test_select_option_raises_on_write_error(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """HomeAssistantError is raised when the device returns a write error."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None

    raw_key, option_string = next(iter(_FIRST_SELECT.value_map.items()))
    mock_client.write_register.return_value = mock_error_result()

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": option_string},
            blocking=True,
        )


# ---------------------------------------------------------------------------
# available — register returns error
# ---------------------------------------------------------------------------


async def test_select_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Select is unavailable when the register read fails."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_client.write_register = AsyncMock(return_value=mock_error_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
