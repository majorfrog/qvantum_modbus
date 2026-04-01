"""Base entity class for the Qvantum Modbus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL

if TYPE_CHECKING:
    from .coordinator import QvantumModbusCoordinator

_LOGGER = logging.getLogger(__name__)


def create_device_info(coordinator: QvantumModbusCoordinator) -> DeviceInfo:
    """Build the DeviceInfo dict for this coordinator's device."""
    entry = coordinator.config_entry
    if entry is None:
        raise RuntimeError(
            "create_device_info called before coordinator was bound to a config entry"
        )
    data = coordinator.data or {}

    # Serial number is stored across five consecutive input registers (_sn_1 … _sn_5).
    sn_parts = [data.get(f"_sn_{i}") for i in range(1, 6)]
    serial_number: str | None = None
    if all(v is not None for v in sn_parts):
        sn_ints = [int(v) for v in sn_parts if v is not None]
        serial_number = str(sn_ints[0]) + "".join(f"{v:03d}" for v in sn_ints[1:])

    # Firmware version is split across _fw_major, _fw_minor, _fw_patch registers.
    fw_parts = [data.get("_fw_major"), data.get("_fw_minor"), data.get("_fw_patch")]
    sw_version: str | None = None
    if all(v is not None for v in fw_parts):
        fw_ints = [int(v) for v in fw_parts if v is not None]
        sw_version = f"{fw_ints[0]}.{fw_ints[1]}.{fw_ints[2]}"

    return DeviceInfo(
        identifiers={(DOMAIN, serial_number or entry.entry_id)},
        name=MODEL,
        manufacturer=MANUFACTURER,
        model=MODEL,
        serial_number=serial_number,
        sw_version=sw_version,
    )


class QvantumModbusEntity(CoordinatorEntity["QvantumModbusCoordinator"]):
    """Base class shared by all Qvantum Modbus entity platforms.

    Provides:
    - ``_attr_has_entity_name = True`` for all subclasses.
    - Per-entity unavailability logging: logs once when the coordinator stops
      updating and again when it recovers, satisfying the HA
      ``log-when-unavailable`` quality scale rule.
    """

    _attr_has_entity_name = True

    @property
    def suggested_object_id(self) -> str | None:
        """Use the register key as the entity ID slug.

        This ensures entity IDs are stable, key-based identifiers
        (e.g. ``number.qvantum_heat_pump_heating_curve_minus20``) rather than
        being derived from the translated entity name, which can produce
        duplicates or unhelpful slugs.
        """
        desc = getattr(self, "entity_description", None)
        return desc.key if desc is not None else None

    def __init__(self, coordinator: QvantumModbusCoordinator) -> None:
        """Initialise the base entity."""
        super().__init__(coordinator)
        self._unavailable_logged = False

    @property
    def available(self) -> bool:
        """Return True when the coordinator last update succeeded.

        Logs a single info message when the entity first becomes unavailable
        and another when it recovers.
        """
        if not super().available:
            if not self._unavailable_logged:
                _LOGGER.info(
                    "Entity %s is unavailable (coordinator update failed)",
                    self.entity_id,
                )
                self._unavailable_logged = True
            return False
        if self._unavailable_logged:
            _LOGGER.info("Entity %s is back online", self.entity_id)
            self._unavailable_logged = False
        return True
