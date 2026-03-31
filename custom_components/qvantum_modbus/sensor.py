"""Sensor platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import (
    COMBINED_SENSOR_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
    ModbusCombinedSensorEntityDescription,
    ModbusSensorEntityDescription,
)

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
    entities: list[SensorEntity] = [
        QvantumModbusSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        QvantumModbusCombinedSensor(coordinator, description)
        for description in COMBINED_SENSOR_DESCRIPTIONS
    )
    async_add_entities(entities)


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
    def native_value(self) -> str | float | None:
        """Return the sensor value, mapped to a string for ENUM sensors."""
        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None
        value_map = self.entity_description.value_map
        if value_map is not None:
            return value_map.get(int(raw))
        return raw


class QvantumModbusCombinedSensor(QvantumModbusEntity, SensorEntity):
    """Sensor whose value is derived by combining multiple Modbus register reads."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusCombinedSensorEntityDescription,
    ) -> None:
        """Initialise the combined sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)

    @property
    def available(self) -> bool:
        """Return True when all component registers have been read successfully."""
        if not super().available:
            return False
        data = self.coordinator.data
        return data is not None and all(
            data.get(comp.key) is not None
            for comp in self.entity_description.components
        )

    @property
    def native_value(self) -> float | str | None:
        """Return the combined value, or None if any component is missing."""
        data = self.coordinator.data
        vals = [data.get(comp.key) for comp in self.entity_description.components]
        if any(v is None for v in vals):
            return None
        desc = self.entity_description
        if desc.value_fn is not None:
            return desc.value_fn(vals)  # type: ignore[arg-type]
        if desc.format_fn is not None:
            return desc.format_fn(vals)  # type: ignore[arg-type]
        return None
