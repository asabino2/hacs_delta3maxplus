"""Switch platform for EcoFlow Delta 3 Max Plus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EcoFlowApiError
from .const import CONF_SELECTED_DEVICES, DATA_COORDINATOR, DOMAIN
from .coordinator import EcoFlowDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class EcoFlowSwitchEntityDescription(SwitchEntityDescription):
    """Describe EcoFlow switches."""

    ac_index: int
    state_key: str


SWITCH_DESCRIPTIONS: tuple[EcoFlowSwitchEntityDescription, ...] = (
    EcoFlowSwitchEntityDescription(
        key="ac1_outlet",
        name="AC1 Outlet",
        ac_index=1,
        state_key="cfgAcOutOpen",
    ),
    EcoFlowSwitchEntityDescription(
        key="ac2_outlet",
        name="AC2 Outlet",
        ac_index=2,
        state_key="cfgAc2OutOpen",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EcoFlow switches from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: EcoFlowDataUpdateCoordinator = data[DATA_COORDINATOR]

    devices_by_sn = {
        str(device.get("sn")): device
        for device in entry.data.get(CONF_SELECTED_DEVICES, [])
        if device.get("sn")
    }

    entities: list[EcoFlowAcSwitch] = []
    for sn, device in devices_by_sn.items():
        for description in SWITCH_DESCRIPTIONS:
            entities.append(
                EcoFlowAcSwitch(
                    coordinator=coordinator,
                    sn=sn,
                    device=device,
                    description=description,
                )
            )

    async_add_entities(entities)


class EcoFlowAcSwitch(CoordinatorEntity[EcoFlowDataUpdateCoordinator], SwitchEntity):
    """Represent one controllable AC outlet switch for one EcoFlow device."""

    entity_description: EcoFlowSwitchEntityDescription

    def __init__(
        self,
        coordinator: EcoFlowDataUpdateCoordinator,
        sn: str,
        device: dict[str, Any],
        description: EcoFlowSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._sn = sn
        self._device = device

        device_name = str(device.get("deviceName") or sn)
        self._attr_name = f"{device_name} {description.name}"
        self._attr_unique_id = f"{DOMAIN}_{sn}_{description.key}"

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.get(self._sn))

    @property
    def is_on(self) -> bool | None:
        payload = self.coordinator.data.get(self._sn, {})
        value = payload.get(self.entity_description.state_key)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            ok = await self.coordinator.api.async_set_ac_outlet_power(
                self._sn,
                self.entity_description.ac_index,
                True,
            )
        except EcoFlowApiError as err:
            raise HomeAssistantError(f"Falha ao ligar AC{self.entity_description.ac_index}: {err}") from err
        if ok:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            ok = await self.coordinator.api.async_set_ac_outlet_power(
                self._sn,
                self.entity_description.ac_index,
                False,
            )
        except EcoFlowApiError as err:
            raise HomeAssistantError(f"Falha ao desligar AC{self.entity_description.ac_index}: {err}") from err
        if ok:
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._sn)},
            name=str(self._device.get("deviceName") or self._sn),
            manufacturer="EcoFlow",
            model=str(self._device.get("productName") or "Delta 3 Max Plus"),
            serial_number=self._sn,
        )
