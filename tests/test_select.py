"""Select platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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
    setup_integration,
) -> None:
    """First select entity is registered after integration setup."""
    assert (
        _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key) is not None
    )


# ---------------------------------------------------------------------------
# current_option — mapped value
# ---------------------------------------------------------------------------


async def test_select_current_option_mapped(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_tcp_client: MagicMock,
) -> None:
    """Select shows the mapped option for the raw register value."""
    # default mock returns 215, which may not be in the value_map;
    # use 0 which is always the first/lowest key in all our selects.
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
    setup_integration: MagicMock,
) -> None:
    """Selecting a valid option writes the corresponding raw int to the register."""
    mock_client = setup_integration
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
    setup_integration: MagicMock,
) -> None:
    """HomeAssistantError is raised when the device returns a write error."""
    mock_client = setup_integration
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
    mock_tcp_client: MagicMock,
) -> None:
    """Select is unavailable when the register read fails."""
    mock_tcp_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.write_register = AsyncMock(return_value=mock_error_result())
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# current_option — returns None when coordinator data has None for the key
# ---------------------------------------------------------------------------


def test_select_current_option_none_when_data_key_is_none() -> None:
    """current_option returns None when coordinator.data[key] is None."""
    from custom_components.qvantum_modbus.select import QvantumModbusSelect

    entity = MagicMock()
    entity.coordinator.data = {_FIRST_SELECT.key: None}
    entity.entity_description.key = _FIRST_SELECT.key

    result = QvantumModbusSelect.current_option.fget(entity)

    assert result is None


# ---------------------------------------------------------------------------
# async_select_option — unknown option raises HomeAssistantError
# ---------------------------------------------------------------------------


async def test_select_option_raises_for_unknown_option(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration: MagicMock,
) -> None:
    """HomeAssistantError is raised when selecting an option not in the value_map."""
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _FIRST_SELECT.key)
    assert entity_id is not None

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "__invalid_option__"},
            blocking=True,
        )


# ---------------------------------------------------------------------------
# async_select_option — unknown option raises HomeAssistantError (line 76)
# Calls the entity method directly to bypass HA's option-list validation.
# ---------------------------------------------------------------------------


async def test_select_option_entity_method_raises_for_unknown() -> None:
    """Entity's async_select_option raises HomeAssistantError for an unmapped option."""
    from custom_components.qvantum_modbus.select import QvantumModbusSelect

    mock_entity = MagicMock()
    mock_entity.entity_description = _FIRST_SELECT

    with pytest.raises(HomeAssistantError):
        await QvantumModbusSelect.async_select_option(
            mock_entity, "__not_a_valid_option__"
        )
