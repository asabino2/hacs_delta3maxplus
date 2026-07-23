"""Sensor platform for EcoFlow Delta 3 Max Plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DESCRIPTION, ATTR_DEVICE_SN, CONF_SELECTED_DEVICES, DATA_COORDINATOR, DOMAIN
from .coordinator import EcoFlowDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class EcoFlowSensorEntityDescription(SensorEntityDescription):
    """Describe EcoFlow telemetry sensors."""

    field_description: str


SENSOR_DESCRIPTIONS: tuple[EcoFlowSensorEntityDescription, ...] = (
    EcoFlowSensorEntityDescription(
        key="powGetAcIn",
        name="AC Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia de entrada AC atual em watts.",
    ),
    EcoFlowSensorEntityDescription(
        key="batteryperc",
        name="Battery Percentage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,   
        state_class=SensorStateClass.MEASUREMENT,
        field_description="Percentual atual da bateria.",
    ),
    EcoFlowSensorEntityDescription(
        key="poweroutsum",
        name="Total Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Soma da potencia total de saida.",
    ),
    EcoFlowSensorEntityDescription(
        key="poweroutAc1",
        name="AC1 Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia de saida atual no canal AC1.",
    ),
    EcoFlowSensorEntityDescription(
        key="poweroutAc2",
        name="AC2 Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia de saida atual no canal AC2.",
    ),
    EcoFlowSensorEntityDescription(
        key="powInSumW",
        name="Total Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Soma total de potencia de entrada em watts.",
    ),
    EcoFlowSensorEntityDescription(
        key="energyBackupEn",
        name="Backup Energy Enabled",
        field_description="Indicador numerico do modo de energia de backup.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsMaxChgSoc",
        name="Max Charge SOC",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        field_description="Limite maximo de carga configurado para o SOC.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsMinDsgSoc",
        name="Min Discharge SOC",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        field_description="Limite minimo de descarga configurado para o SOC.",
    ),
    EcoFlowSensorEntityDescription(
        key="powGetTypec3",
        name="USB-C3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia atual da porta USB-C3.",
    ),
    EcoFlowSensorEntityDescription(
        key="powGetTypec1",
        name="USB-C1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia atual da porta USB-C1.",
    ),
    EcoFlowSensorEntityDescription(
        key="powGetTypec2",
        name="USB-C2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia atual da porta USB-C2.",
    ),
    EcoFlowSensorEntityDescription(
        key="PowerUsbTypeC1",
        name="USB-C1 Absolute Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia absoluta (valor positivo) da porta USB-C1.",
    ),
    EcoFlowSensorEntityDescription(
        key="PowerUsbTypeC2",
        name="USB-C2 Absolute Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia absoluta (valor positivo) da porta USB-C2.",
    ),
    EcoFlowSensorEntityDescription(
        key="PowerUsbTypeC3",
        name="USB-C3 Absolute Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER
        field_description="Potencia absoluta (valor positivo) da porta USB-C3.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsDsgRemTime",
        name="Remaining Discharge Time Seconds",
        state_class=SensorStateClass.MEASUREMENT,
        field_description="Tempo restante estimado de descarga em segundos.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsDsgRemTimeFmt",
        name="Remaining Discharge Time",
        field_description="Tempo restante estimado de descarga no formato HH:MM:SS.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsChgDsgState",
        name="Charge/Discharge State Code",
        state_class=SensorStateClass.MEASUREMENT,
        field_description="Codigo de estado: 0=Idle, 1=Discharging, 2=Charging.",
    ),
    EcoFlowSensorEntityDescription(
        key="cmsChgDsgStateDesc",
        name="Charge/Discharge State Description",
        field_description="Descricao legivel do estado de carga/descarga.",
    ),
    EcoFlowSensorEntityDescription(
        key="ac1OutStatus",
        name="AC1 Out Status",
        field_description="Status da saida AC1: on quando flowInfoAcOut for diferente de 4, off quando for 4.",
    ),
    EcoFlowSensorEntityDescription(
        key="ac2OutStatus",
        name="AC2 Out Status",
        field_description="Status da saida AC2: on quando flowInfoAc2Out for diferente de 4, off quando for 4.",
    ),
    EcoFlowSensorEntityDescription(
        key="out12vStatus",
        name="12v Out Status",
        field_description="Status da saida 12v: on quando flowInfo12v for diferente de 4, off quando for 4.",
    ),
    EcoFlowSensorEntityDescription(
        key="xboostEn",
        name="X-Boost",
        field_description="Status do X-Boost com base na tag xboostEn: true=ligado, false=desligado.",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EcoFlow sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: EcoFlowDataUpdateCoordinator = data[DATA_COORDINATOR]

    devices_by_sn = {
        str(device.get("sn")): device
        for device in entry.data.get(CONF_SELECTED_DEVICES, [])
        if device.get("sn")
    }

    entities: list[EcoFlowTelemetrySensor] = []
    for sn, device in devices_by_sn.items():
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                EcoFlowTelemetrySensor(
                    coordinator=coordinator,
                    sn=sn,
                    device=device,
                    description=description,
                )
            )

    async_add_entities(entities)


class EcoFlowTelemetrySensor(CoordinatorEntity[EcoFlowDataUpdateCoordinator], SensorEntity):
    """Represent a telemetry field for one EcoFlow device."""

    entity_description: EcoFlowSensorEntityDescription

    def __init__(
        self,
        coordinator: EcoFlowDataUpdateCoordinator,
        sn: str,
        device: dict[str, Any],
        description: EcoFlowSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._sn = sn
        self._device = device

        device_name = str(device.get("deviceName") or sn)
        self._attr_name = f"{device_name} {description.name}"
        self._attr_unique_id = f"{DOMAIN}_{sn}_{description.key}"

    @property
    def native_value(self) -> Any:
        payload = self.coordinator.data.get(self._sn, {})
        return payload.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        payload = self.coordinator.data.get(self._sn, {})
        return bool(payload) and self.entity_description.key in payload

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_DEVICE_SN: self._sn,
            ATTR_DESCRIPTION: self.entity_description.field_description,
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._sn)},
            name=str(self._device.get("deviceName") or self._sn),
            manufacturer="EcoFlow",
            model=str(self._device.get("productName") or "Delta 3 Max Plus"),
            serial_number=self._sn,
        )
