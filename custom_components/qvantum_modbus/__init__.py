"""Qvantum Modbus integration."""

from __future__ import annotations

import voluptuous as vol

from typing import Any

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONF_STOPBITS,
    CONNECTION_TYPE_RTU,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_UNIT_ID,
    DEFAULT_STOPBITS,
    DOMAIN,
)
from .coordinator import QvantumModbusCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type QvantumModbusConfigEntry = ConfigEntry[QvantumModbusCoordinator]

# ---------------------------------------------------------------------------
# YAML configuration schema
# ---------------------------------------------------------------------------
# Accepts either a single mapping or a list of mappings under the domain key.
# TCP example:
#   qvantum_modbus:
#     connection_type: tcp
#     host: 192.168.1.100
#     port: 502          # optional, default 502
#     unit_id: 1         # optional, default 1
#
# RTU example:
#   qvantum_modbus:
#     - connection_type: rtu
#       port: /dev/ttyUSB0
#       unit_id: 1
#       baudrate: 9600
#       bytesize: 8
#       parity: N
#       stopbits: 1


def _validate_device_config(config: dict[str, Any]) -> dict[str, Any]:
    """Require host when connection_type is tcp."""
    if config[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TCP and not config.get(
        CONF_HOST
    ):
        raise vol.Invalid(
            f"{CONF_HOST!r} is required when connection_type is {CONNECTION_TYPE_TCP!r}"
        )
    return config


_DEVICE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(CONF_CONNECTION_TYPE): vol.In(
                [CONNECTION_TYPE_TCP, CONNECTION_TYPE_RTU]
            ),
            # TCP: hostname/IP; not needed for RTU
            vol.Optional(CONF_HOST): cv.string,
            # TCP: integer port; RTU: serial device path string
            vol.Optional(CONF_PORT): vol.Any(cv.port, cv.string),
            vol.Optional(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
                int, vol.Range(min=1, max=247)
            ),
            # RTU-only options (ignored for TCP)
            vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
            vol.Optional(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.In([5, 6, 7, 8]),
            vol.Optional(CONF_PARITY, default=DEFAULT_PARITY): vol.In(["N", "E", "O"]),
            vol.Optional(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.In([1, 2]),
        }
    ),
    _validate_device_config,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [_DEVICE_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Import entries defined in configuration.yaml."""
    for device_config in config.get(DOMAIN, []):
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=device_config,
        )
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entry versions to the current schema."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: QvantumModbusConfigEntry
) -> bool:
    """Set up Qvantum Modbus from a config entry."""
    coordinator = QvantumModbusCoordinator(hass, entry)

    # Perform the first data fetch; raises ConfigEntryNotReady if unreachable
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Disconnect from the Modbus device cleanly when the entry is unloaded
    entry.async_on_unload(coordinator.async_disconnect)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: QvantumModbusConfigEntry
) -> bool:
    """Unload a Qvantum Modbus config entry."""
    return bool(await hass.config_entries.async_unload_platforms(entry, PLATFORMS))
