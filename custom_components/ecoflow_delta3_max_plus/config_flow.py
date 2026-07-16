"""Config flow for EcoFlow Delta 3 Max Plus integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EcoFlowApiClient, EcoFlowApiError, EcoFlowAuthError
from .const import CONF_ACCESS_KEY, CONF_SECRET_KEY, CONF_SELECTED_DEVICES, CONF_SELECTED_SNS, DOMAIN


class EcoFlowDelta3MaxPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EcoFlow Delta 3 Max Plus."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            access_key = user_input[CONF_ACCESS_KEY].strip()
            secret_key = user_input[CONF_SECRET_KEY].strip()

            try:
                session = async_get_clientsession(self.hass)
                api = EcoFlowApiClient(session, access_key, secret_key)
                raw_devices = await api.async_list_account_devices_raw()
                devices = api.map_devices_response(raw_devices.get("data", {}))
            except EcoFlowAuthError:
                errors["base"] = "invalid_auth"
            except EcoFlowApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._credentials = {
                        CONF_ACCESS_KEY: access_key,
                        CONF_SECRET_KEY: secret_key,
                    }
                    self._devices = devices
                    return await self.async_step_select_devices()

        schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_KEY): str,
                vol.Required(CONF_SECRET_KEY): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_devices(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        options: list[selector.SelectOptionDict] = []
        for device in self._devices:
            sn = str(device.get("sn", "")).strip()
            if not sn:
                continue
            device_name = str(device.get("deviceName") or "EcoFlow Device")
            product_name = str(device.get("productName") or "Unknown Product")
            online = device.get("online")
            status = "online" if online is True else "offline" if online is False else "unknown"
            label = f"{device_name} ({product_name}) - SN: {sn} - {status}"
            options.append(selector.SelectOptionDict(value=sn, label=label))

        if user_input is not None:
            selected_sns = user_input.get(CONF_SELECTED_SNS, [])
            if not selected_sns:
                errors["base"] = "select_at_least_one"
            else:
                selected_set = set(selected_sns)
                selected_devices = [
                    device
                    for device in self._devices
                    if str(device.get("sn", "")).strip() in selected_set
                ]

                for entry in self._async_current_entries():
                    existing = set(entry.data.get(CONF_SELECTED_SNS, []))
                    if existing == selected_set:
                        return self.async_abort(reason="already_configured")

                title = "EcoFlow Delta 3 Max Plus"
                if len(selected_devices) == 1:
                    title = f"EcoFlow {selected_devices[0].get('deviceName') or selected_devices[0].get('sn')}"

                return self.async_create_entry(
                    title=title,
                    data={
                        **self._credentials,
                        CONF_SELECTED_SNS: list(selected_set),
                        CONF_SELECTED_DEVICES: selected_devices,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SELECTED_SNS,
                    default=[str(device.get("sn")) for device in self._devices if device.get("sn")],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="select_devices", data_schema=schema, errors=errors)
