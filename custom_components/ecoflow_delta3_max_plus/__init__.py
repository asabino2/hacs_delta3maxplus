"""EcoFlow Delta 3 Max Plus integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EcoFlowApiClient
from .const import (
    CONF_ACCESS_KEY,
    CONF_SECRET_KEY,
    CONF_SELECTED_DEVICES,
    CONF_SELECTED_SNS,
    DATA_API,
    DATA_COORDINATOR,
    DATA_DEVICES,
    DOMAIN,
    SERVICE_TURN_OFF_AC1,
    SERVICE_TURN_OFF_AC2,
)
from .coordinator import EcoFlowDataUpdateCoordinator

SERVICE_FIELD_SN = "sn"

PLATFORMS: list[Platform] = [Platform.SENSOR]
SERVICES_KEY = "services_registered"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EcoFlow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = EcoFlowApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_ACCESS_KEY],
        entry.data[CONF_SECRET_KEY],
    )

    selected_sns = list(entry.data.get(CONF_SELECTED_SNS, []))
    selected_devices = list(entry.data.get(CONF_SELECTED_DEVICES, []))

    coordinator = EcoFlowDataUpdateCoordinator(hass, api, selected_sns)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_API: api,
        DATA_COORDINATOR: coordinator,
        DATA_DEVICES: selected_devices,
    }

    await _async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if DOMAIN in hass.data:
        has_entries = any(key != SERVICES_KEY for key in hass.data[DOMAIN])
        if not has_entries:
            _async_unregister_services(hass)
            hass.data[DOMAIN].pop(SERVICES_KEY, None)
            if not hass.data[DOMAIN]:
                hass.data.pop(DOMAIN, None)

    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.data[DOMAIN].get(SERVICES_KEY):
        return

    schema = vol.Schema({vol.Optional(SERVICE_FIELD_SN): cv.string})

    async def _register(name: str, ac_index: int) -> None:
        async def _handler(call: ServiceCall) -> None:
            await _async_handle_power_service(hass, call, ac_index=ac_index)

        hass.services.async_register(DOMAIN, name, _handler, schema=schema)

    await _register(SERVICE_TURN_OFF_AC1, 1)
    await _register(SERVICE_TURN_OFF_AC2, 2)

    hass.data[DOMAIN][SERVICES_KEY] = True


def _async_unregister_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_TURN_OFF_AC1):
        hass.services.async_remove(DOMAIN, SERVICE_TURN_OFF_AC1)
    if hass.services.has_service(DOMAIN, SERVICE_TURN_OFF_AC2):
        hass.services.async_remove(DOMAIN, SERVICE_TURN_OFF_AC2)


def _iter_entries(hass: HomeAssistant):
    domain_data = hass.data.get(DOMAIN, {})
    for entry_id, data in domain_data.items():
        if entry_id == SERVICES_KEY:
            continue
        yield data


async def _async_handle_power_service(hass: HomeAssistant, call: ServiceCall, ac_index: int) -> None:
    requested_sn = str(call.data.get(SERVICE_FIELD_SN, "")).strip()

    targets: list[tuple[EcoFlowApiClient, EcoFlowDataUpdateCoordinator, str]] = []
    refresh_callbacks: set[Callable[[], Any]] = set()

    for data in _iter_entries(hass):
        api: EcoFlowApiClient = data[DATA_API]
        coordinator: EcoFlowDataUpdateCoordinator = data[DATA_COORDINATOR]
        devices: list[dict[str, Any]] = data[DATA_DEVICES]

        for device in devices:
            sn = str(device.get("sn", "")).strip()
            if not sn:
                continue
            if requested_sn and sn != requested_sn:
                continue
            targets.append((api, coordinator, sn))
            refresh_callbacks.add(coordinator.async_request_refresh)

    if not targets:
        raise HomeAssistantError("Nenhum inversor encontrado para o SN informado")

    failed: list[str] = []
    for api, _coordinator, sn in targets:
        ok = await api.async_set_ac_outlet_power(sn, ac_index, False)
        if not ok:
            failed.append(sn)

    for refresh in refresh_callbacks:
        await refresh()

    if failed:
        raise HomeAssistantError(f"Falha ao desligar AC{ac_index} para SN(s): {', '.join(failed)}")
