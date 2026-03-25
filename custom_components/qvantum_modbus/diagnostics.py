"""Diagnostics support for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import QvantumModbusConfigEntry

# No credentials in Modbus; the set is empty but kept for consistency with
# the standard HA diagnostics pattern in case sensitive fields are added later.
TO_REDACT: set[str] = set()


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: QvantumModbusConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "update_interval": str(coordinator.update_interval),
            "last_update_success": coordinator.last_update_success,
            "consecutive_failures": coordinator.consecutive_failures,
        },
        "data": coordinator.data,
    }
