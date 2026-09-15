"""Sensor platform for the Qvantum Modbus integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .alarm_codes import ALARM_CODES
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
        if self.entity_description.alarm_code:
            return str(int(raw))
        value_map = self.entity_description.value_map
        if value_map is not None:
            mapped = value_map.get(int(raw))
            if mapped is None:
                _LOGGER.warning(
                    "Unmapped value %d for %s",
                    int(raw),
                    self.entity_description.key,
                )
            return mapped
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return descriptive metadata for alarm-code sensors."""
        if not self.entity_description.alarm_code:
            return None

        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None

        code = int(raw)
        info = ALARM_CODES.get(code)
        if info is None:
            return {
                "code": code,
                "label": f"Unknown alarm code ({code})",
                "trigger": None,
                "possible_cause": None,
                "product_action": None,
                "service_action": None,
            }

        return {
            "code": code,
            "label": info.label,
            "trigger": info.trigger,
            "possible_cause": info.possible_cause,
            "product_action": info.product_action,
            "service_action": info.service_action,
        }


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
