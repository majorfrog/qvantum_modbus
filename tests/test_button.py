"""Button platform tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.models import BUTTON_DESCRIPTIONS

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


_BUTTON_DESC = BUTTON_DESCRIPTIONS[0]


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_button_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Button entity is registered after integration setup."""
    await _setup(hass, mock_tcp_config_entry)

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get_entity_id(
        "button",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_{_BUTTON_DESC.key}",
    )
    assert entry is not None


# ---------------------------------------------------------------------------
# async_press — happy path
# ---------------------------------------------------------------------------


async def test_button_press_writes_configured_value(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Pressing the button writes the configured write_value to the register."""
    mock_client = await _setup(hass, mock_tcp_config_entry)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "button",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_{_BUTTON_DESC.key}",
    )
    assert entity_id is not None

    mock_client.write_register.reset_mock()
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    mock_client.write_register.assert_called_once()
    call_kwargs = mock_client.write_register.call_args.kwargs
    assert call_kwargs["value"] == _BUTTON_DESC.write_value
    assert call_kwargs["address"] == _BUTTON_DESC.address


# ---------------------------------------------------------------------------
# async_press — write error propagates
# ---------------------------------------------------------------------------


async def test_button_press_raises_on_write_error(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """HomeAssistantError is raised when the device returns a write error."""
    mock_client = await _setup(hass, mock_tcp_config_entry)

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "button",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_{_BUTTON_DESC.key}",
    )
    assert entity_id is not None

    mock_client.write_register.return_value = mock_error_result()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button", "press", {"entity_id": entity_id}, blocking=True
        )
