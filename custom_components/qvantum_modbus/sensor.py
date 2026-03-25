"""Sensor platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import SENSOR_DESCRIPTIONS, ModbusSensorEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus sensor entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class QvantumModbusSensor(QvantumModbusEntity, SensorEntity):
    """Represents a single Modbus register as a Home Assistant sensor."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)
        self._attr_suggested_display_precision = description.precision

    # ------------------------------------------------------------------
    # CoordinatorEntity / SensorEntity interface
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True when coordinator succeeded and the register has a value."""
        if not super().available:
            return False
        return (
            self.coordinator.data is not None
            and self.coordinator.data.get(self.entity_description.key) is not None
        )

    @property
    def native_value(self) -> float | None:
        """Return the current sensor value (already decoded and scaled)."""
        return self.coordinator.data.get(self.entity_description.key)
