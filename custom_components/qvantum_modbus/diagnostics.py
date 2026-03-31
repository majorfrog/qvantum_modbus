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

# Raw component register keys in coordinator.data that back the sensitive
# combined sensors; these must also be redacted in the raw data snapshot.
_SENSITIVE_COMPONENT_KEYS: frozenset[str] = frozenset(
    {
        "_ip_1",
        "_ip_2",
        "_ip_3",
        "_ip_4",
        "_sn_1",
        "_sn_2",
        "_sn_3",
        "_sn_4",
        "_sn_5",
    }
)


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: QvantumModbusConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data: dict[str, Any] = dict(coordinator.data or {})

    # Compute derived values from raw component registers.
    sn_parts = [data.get(f"_sn_{i}") for i in range(1, 6)]
    serial_number: str | None = None
    if all(v is not None for v in sn_parts):
        sn_ints = [int(v) for v in sn_parts if v is not None]
        serial_number = str(sn_ints[0]) + "".join(f"{v:03d}" for v in sn_ints[1:])

    fw_parts = [data.get("_fw_major"), data.get("_fw_minor"), data.get("_fw_patch")]
    fw_version: str | None = None
    if all(v is not None for v in fw_parts):
        fw_ints = [int(v) for v in fw_parts if v is not None]
        fw_version = f"{fw_ints[0]}.{fw_ints[1]}.{fw_ints[2]}"

    ip_parts = [data.get(f"_ip_{i}") for i in range(1, 5)]
    ip_address: str | None = None
    if all(v is not None for v in ip_parts):
        ip_address = ".".join(str(int(v)) for v in ip_parts if v is not None)

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "update_interval": str(coordinator.update_interval),
            "last_update_success": coordinator.last_update_success,
            "consecutive_failures": coordinator.consecutive_failures,
        },
        "device": async_redact_data(
            {
                "serial_number": serial_number,
                "fw_version": fw_version,
                "ip_address": ip_address,
            },
            TO_REDACT,
        ),
        "data": async_redact_data(data, TO_REDACT | _SENSITIVE_COMPONENT_KEYS),
    }
