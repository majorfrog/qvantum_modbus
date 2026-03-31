"""Button platform tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.models import BUTTON_DESCRIPTIONS

from .fixtures import mock_error_result


_BUTTON_DESC = BUTTON_DESCRIPTIONS[0]


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_button_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """Button entity is registered after integration setup."""
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
    setup_integration: MagicMock,
) -> None:
    """Pressing the button writes the configured write_value to the register."""
    mock_client = setup_integration

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
    setup_integration: MagicMock,
) -> None:
    """HomeAssistantError is raised when the device returns a write error."""
    mock_client = setup_integration

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
