"""Qvantum Modbus integration."""

from __future__ import annotations

import asyncio
import logging
import voluptuous as vol

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState, SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_DURATION_HOURS,
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
    DHW_MODE_EXTRA,
    DHW_MODE_KEY,
    DHW_MODE_NORMAL,
    DOMAIN,
    SERVICE_CANCEL_EXTRA_HOT_WATER,
    SERVICE_START_EXTRA_HOT_WATER,
)
from .coordinator import QvantumModbusCoordinator
from .models import SELECT_DESCRIPTIONS

_LOGGER = logging.getLogger(__name__)

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
    """Import entries defined in configuration.yaml and register service actions."""
    for device_config in config.get(DOMAIN, []):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=device_config,
            )
        )

    # -------------------------------------------------------------------------
    # Service: start_extra_hot_water
    # Sets DHW mode to "extra" for the given number of hours, then restores the
    # previous mode. Operates on every loaded config entry for this domain.
    # -------------------------------------------------------------------------
    _boost_tasks: dict[str, asyncio.Task[None]] = {}

    # Resolve the Modbus address of the dhw_mode holding register once at setup
    # time so we don't hard-code a magic number here.
    _dhw_select = next((d for d in SELECT_DESCRIPTIONS if d.key == DHW_MODE_KEY), None)
    if _dhw_select is None:
        _LOGGER.error(
            "Could not find dhw_mode select description — services will not be registered"
        )
        return True

    _dhw_address: int = _dhw_select.address
    # Map option strings → raw register values (inverse of value_map)
    _dhw_option_to_raw: dict[str, int] = {
        v: k for k, v in _dhw_select.value_map.items()
    }

    def _get_coordinators() -> list[QvantumModbusCoordinator]:
        """Return coordinators for every loaded config entry."""
        coordinators: list[QvantumModbusCoordinator] = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.state is ConfigEntryState.LOADED:
                coordinators.append(entry.runtime_data)
        return coordinators

    async def _set_dhw_mode(coordinator: QvantumModbusCoordinator, mode: str) -> None:
        """Write a DHW mode option to the device holding register."""
        raw = _dhw_option_to_raw.get(mode)
        if raw is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_dhw_mode",
                translation_placeholders={"mode": mode},
            )
        await coordinator.write_holding_register(_dhw_address, raw)
        await coordinator.async_request_refresh()

    def _current_dhw_mode(coordinator: QvantumModbusCoordinator) -> str:
        """Return the current DHW mode option string from coordinator data."""
        raw = (coordinator.data or {}).get(DHW_MODE_KEY)
        if raw is None:
            return DHW_MODE_NORMAL
        mapped = _dhw_select.value_map.get(int(raw))
        return mapped if mapped is not None else DHW_MODE_NORMAL

    async def _boost_worker(
        coordinator: QvantumModbusCoordinator,
        previous_mode: str,
        duration_seconds: float,
    ) -> None:
        """Run the timed boost: wait, then restore the previous mode."""
        try:
            await asyncio.sleep(duration_seconds)
        except asyncio.CancelledError:
            pass  # Cancelled by cancel_extra_hot_water — restore mode below.
        finally:
            try:
                await _set_dhw_mode(coordinator, previous_mode)
            except Exception:
                _LOGGER.exception(
                    "Failed to restore DHW mode to %s after boost", previous_mode
                )

    async def _handle_start_extra_hot_water(call: ServiceCall) -> None:
        """Handle the start_extra_hot_water service call."""
        duration_hours: float = call.data[ATTR_DURATION_HOURS]
        duration_seconds = duration_hours * 3600

        coordinators = _get_coordinators()
        if not coordinators:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_loaded_entry",
            )

        for coordinator in coordinators:
            entry_id = coordinator.config_entry.entry_id  # type: ignore[union-attr]

            # Cancel any running boost for this entry first.
            if existing := _boost_tasks.get(entry_id):
                existing.cancel()

            # Save the current mode (skip if already in extra so original is kept).
            previous_mode = _current_dhw_mode(coordinator)
            if previous_mode == DHW_MODE_EXTRA:
                previous_mode = DHW_MODE_NORMAL

            await _set_dhw_mode(coordinator, DHW_MODE_EXTRA)

            task = hass.async_create_task(
                _boost_worker(coordinator, previous_mode, duration_seconds),
                name=f"qvantum_boost_{entry_id}",
            )
            _boost_tasks[entry_id] = task

            def _cleanup(fut: asyncio.Task[None], eid: str = entry_id) -> None:
                _boost_tasks.pop(eid, None)

            task.add_done_callback(_cleanup)

        _LOGGER.debug("Extra hot water boost started for %.1f hours", duration_hours)

    async def _handle_cancel_extra_hot_water(call: ServiceCall) -> None:
        """Handle the cancel_extra_hot_water service call."""
        coordinators = _get_coordinators()
        if not coordinators:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_loaded_entry",
            )

        for coordinator in coordinators:
            entry_id = coordinator.config_entry.entry_id  # type: ignore[union-attr]
            if task := _boost_tasks.get(entry_id):
                task.cancel()
                # _boost_worker's finally block will restore the mode.
            else:
                _LOGGER.debug(
                    "cancel_extra_hot_water called but no boost was running for %s",
                    entry_id,
                )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_EXTRA_HOT_WATER,
        _handle_start_extra_hot_water,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_DURATION_HOURS, default=4.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.5, max=24.0)
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_EXTRA_HOT_WATER,
        _handle_cancel_extra_hot_water,
        schema=vol.Schema({}),
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
