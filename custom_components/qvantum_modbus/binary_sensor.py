"""Binary sensor platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import BINARY_SENSOR_DESCRIPTIONS, ModbusBinarySensorEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus binary sensor entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class QvantumModbusBinarySensor(QvantumModbusEntity, BinarySensorEntity):
    """Represents a Modbus register (or a single bit thereof) as a binary sensor."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)

    @property
    def available(self) -> bool:
        """Return True when the coordinator succeeded and the register has a value."""
        if not super().available:
            return False
        return (
            self.coordinator.data is not None
            and self.coordinator.data.get(self.entity_description.key) is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when the register value (or extracted bit) is non-zero."""
        val = self.coordinator.data.get(self.entity_description.key)
        if val is None:
            return None
        return bool(val)
