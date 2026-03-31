"""Number platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.models import NUMBER_DESCRIPTIONS

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
    return er.async_get(hass).async_get_entity_id("number", DOMAIN, f"{entry_id}_{key}")


# Use the first number description with a scale of 1.0 for simple integer tests
_DESC = next(d for d in NUMBER_DESCRIPTIONS if d.scale == 1.0)


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_number_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """First number entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)
    assert _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key) is not None


# ---------------------------------------------------------------------------
# native_value
# ---------------------------------------------------------------------------


async def test_number_native_value(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Number reports the register value multiplied by the scale."""
    raw = 50
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(
            value=raw, count=kw.get("count", 1)
        )
    )
    mock_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(
            value=raw, count=kw.get("count", 1)
        )
    )
    mock_client.write_register = AsyncMock(return_value=mock_register_result(value=raw))

    await _setup(hass, mock_tcp_config_entry, mock_client)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    # scale=1.0 → native_value == raw
    assert float(state.state) == pytest.approx(raw * _DESC.scale)


# ---------------------------------------------------------------------------
# async_set_native_value
# ---------------------------------------------------------------------------


async def test_number_set_value_writes_scaled_raw(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Setting a value writes round(value / scale) to the register."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key)
    assert entity_id is not None

    # Pick a value within the allowed range for _DESC
    target = (_DESC.native_min_value + _DESC.native_max_value) / 2
    expected_raw = round(target / _DESC.scale)

    mock_client.write_register.reset_mock()
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": target},
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_client.write_register.assert_called_once()
    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == expected_raw


async def test_number_set_value_raises_on_write_error(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """HomeAssistantError is raised when the device returns a write error."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key)
    assert entity_id is not None

    mock_client.write_register.return_value = mock_error_result()
    target = (_DESC.native_min_value + _DESC.native_max_value) / 2

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": target},
            blocking=True,
        )


async def test_number_set_value_raises_on_out_of_range(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """HomeAssistantError is raised when the raw value exceeds register bounds."""
    mock_client = await _setup(hass, mock_tcp_config_entry)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key)
    assert entity_id is not None

    # Force a value beyond max to bypass HA frontend validation
    over_max = _DESC.native_max_value + 1000.0

    with pytest.raises((HomeAssistantError, ValueError)):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": entity_id, "value": over_max},
            blocking=True,
        )


# ---------------------------------------------------------------------------
# available — register returns error
# ---------------------------------------------------------------------------


async def test_number_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Number is unavailable when the register read fails."""
    mock_client = MagicMock()
    mock_client.connected = True
    mock_client.connect = AsyncMock(return_value=True)
    mock_client.close = MagicMock()
    mock_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_client.write_register = AsyncMock(return_value=mock_error_result())

    await _setup(hass, mock_tcp_config_entry, mock_client)
    entity_id = _entity_id(hass, mock_tcp_config_entry.entry_id, _DESC.key)
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"
