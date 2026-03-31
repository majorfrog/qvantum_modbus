"""Diagnostics support for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import QvantumModbusConfigEntry

# Redact connection details and device-specific identifiers that could
# expose the local network layout.
TO_REDACT: set[str] = {CONF_HOST, "ip_address", "serial_number"}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: QvantumModbusConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "update_interval": str(coordinator.update_interval),
            "last_update_success": coordinator.last_update_success,
            "consecutive_failures": coordinator.consecutive_failures,
        },
        "device": {
            "serial_number": data.get("serial_number"),
            "fw_version": data.get("fw_version"),
            "ip_address": data.get("ip_address"),
        },
        "data": data,
    }
