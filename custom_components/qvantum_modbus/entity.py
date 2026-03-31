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
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=MODEL,
        manufacturer=MANUFACTURER,
        model=MODEL,
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
