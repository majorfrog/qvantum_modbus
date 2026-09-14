"""__init__.py tests — covers YAML import, CONFIG_SCHEMA validation, async_setup."""

from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.qvantum_modbus.const import (
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_TCP,
    DOMAIN,
)

from .fixtures import MOCK_TCP_ENTRY_DATA


# ---------------------------------------------------------------------------
# CONFIG_SCHEMA validation — TCP missing host raises vol.Invalid
# ---------------------------------------------------------------------------


def test_validate_device_config_tcp_missing_host_raises() -> None:
    """CONFIG_SCHEMA raises vol.MultipleInvalid when TCP config is missing a host."""
    from custom_components.qvantum_modbus import CONFIG_SCHEMA

    with pytest.raises(vol.MultipleInvalid):
        CONFIG_SCHEMA(
            {
                DOMAIN: [
                    {
                        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                        # CONF_HOST intentionally omitted
                    }
                ]
            }
        )


def test_validate_device_config_valid_tcp_returns_config() -> None:
    """CONFIG_SCHEMA returns the processed config for a valid TCP entry."""
    from custom_components.qvantum_modbus import CONFIG_SCHEMA
    from homeassistant.const import CONF_HOST

    result = CONFIG_SCHEMA(
        {
            DOMAIN: [
                {
                    CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                    CONF_HOST: "192.168.1.100",
                }
            ]
        }
    )
    assert result[DOMAIN][0][CONF_HOST] == "192.168.1.100"


# ---------------------------------------------------------------------------
# async_setup — iterates over YAML entries and calls async_init (lines 108/118)
# ---------------------------------------------------------------------------


async def test_async_setup_with_yaml_config_imports_entry(
    hass: HomeAssistant,
    mock_tcp_client,
) -> None:
    """async_setup triggers a config-flow import for each entry in configuration.yaml."""
    from custom_components.qvantum_modbus import async_setup

    result = await async_setup(hass, {DOMAIN: [MOCK_TCP_ENTRY_DATA]})

    assert result is True

    # async_setup schedules the flow via async_create_task; yield to the event
    # loop so the task actually runs before we inspect entries/flows.
    await hass.async_block_till_done()

    # async_init queues a SOURCE_IMPORT flow; verify it was created/completed
    entries = hass.config_entries.async_entries(DOMAIN)
    # The flow may have completed as a new entry by now; either way, at least one
    # entry or in-progress flow must exist.
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert entries or flows, "Expected at least one config entry or in-progress flow"


async def test_async_setup_with_empty_config_returns_true(
    hass: HomeAssistant,
) -> None:
    """async_setup returns True even with an empty domain config."""
    from custom_components.qvantum_modbus import async_setup

    result = await async_setup(hass, {})

    assert result is True


async def test_async_migrate_entry_returns_true(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """async_migrate_entry always returns True (no data migration needed yet)."""
    from custom_components.qvantum_modbus import async_migrate_entry

    result = await async_migrate_entry(hass, mock_tcp_config_entry)

    assert result is True
