"""Config flow for EcoFlow Delta 3 Max Plus integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EcoFlowApiClient, EcoFlowApiError, EcoFlowAuthError
from .const import (
    CONF_ACCESS_KEY,
    CONF_SCAN_INTERVAL_MODE,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SECRET_KEY,
    CONF_SELECTED_DEVICES,
    CONF_SELECTED_SNS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SCAN_INTERVAL_MODE_CUSTOM,
    SCAN_INTERVAL_MODE_DEFAULT,
)


class _EcoFlowDelta3MaxPlusConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for EcoFlow Delta 3 Max Plus."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return EcoFlowDelta3MaxPlusOptionsFlow(config_entry)

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


class EcoFlowDelta3MaxPlusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for EcoFlow Delta 3 Max Plus."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Select interval mode."""
        errors: dict[str, str] = {}

        default_seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())
        mode = self._config_entry.options.get(CONF_SCAN_INTERVAL_MODE)
        if mode not in (SCAN_INTERVAL_MODE_DEFAULT, SCAN_INTERVAL_MODE_CUSTOM):
            mode = (
                SCAN_INTERVAL_MODE_CUSTOM
                if CONF_SCAN_INTERVAL_SECONDS in self._config_entry.options
                else SCAN_INTERVAL_MODE_DEFAULT
            )

        if user_input is not None:
            selected_mode = user_input.get(CONF_SCAN_INTERVAL_MODE, SCAN_INTERVAL_MODE_DEFAULT)
            if selected_mode == SCAN_INTERVAL_MODE_DEFAULT:
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL_MODE: SCAN_INTERVAL_MODE_DEFAULT},
                )
            return await self.async_step_custom(
                {
                    CONF_SCAN_INTERVAL_SECONDS: int(
                        self._config_entry.options.get(CONF_SCAN_INTERVAL_SECONDS, default_seconds)
                    )
                }
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL_MODE, default=mode): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=SCAN_INTERVAL_MODE_DEFAULT,
                                label="Default Scan Interval",
                            ),
                            selector.SelectOptionDict(
                                value=SCAN_INTERVAL_MODE_CUSTOM,
                                label="Custom",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_custom(self, user_input: dict[str, Any] | None = None):
        """Set custom scan interval seconds."""
        errors: dict[str, str] = {}

        default_seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())
        current_seconds = int(self._config_entry.options.get(CONF_SCAN_INTERVAL_SECONDS, default_seconds))

        if user_input is not None:
            selected_seconds = user_input.get(CONF_SCAN_INTERVAL_SECONDS, current_seconds)
            try:
                selected_seconds = int(selected_seconds)
            except (TypeError, ValueError):
                errors["base"] = "invalid_scan_interval"
            else:
                if selected_seconds < 1:
                    errors["base"] = "invalid_scan_interval"

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SCAN_INTERVAL_MODE: SCAN_INTERVAL_MODE_CUSTOM,
                        CONF_SCAN_INTERVAL_SECONDS: selected_seconds,
                    },
                )
            current_seconds = int(selected_seconds) if isinstance(selected_seconds, int) else current_seconds

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL_SECONDS, default=current_seconds): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=86400,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                )
            }
        )
        return self.async_show_form(step_id="custom", data_schema=schema, errors=errors)


try:
    class EcoFlowDelta3MaxPlusConfigFlow(_EcoFlowDelta3MaxPlusConfigFlow, domain=DOMAIN):
        """Config flow for modern Home Assistant versions."""

except TypeError:
    EcoFlowDelta3MaxPlusConfigFlow = config_entries.HANDLERS.register(DOMAIN)(
        _EcoFlowDelta3MaxPlusConfigFlow
    )
