"""Data coordinator for EcoFlow Delta 3 Max Plus."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcoFlowApiClient, EcoFlowApiError, EcoFlowAuthError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EcoFlowDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that fetches telemetry for all selected devices."""

    def __init__(self, hass: HomeAssistant, api: EcoFlowApiClient, sns: list[str]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="EcoFlow Delta 3 Max Plus",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.sns = sns

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        next_data: dict[str, dict[str, Any]] = {}
        failed = 0

        for sn in self.sns:
            try:
                next_data[sn] = await self.api.async_get_mapped_data(sn)
            except EcoFlowAuthError as err:
                raise UpdateFailed(f"Authentication failed: {err}") from err
            except EcoFlowApiError as err:
                failed += 1
                _LOGGER.warning("Failed to update telemetry for SN %s: %s", sn, err)
                if self.data and sn in self.data:
                    next_data[sn] = self.data[sn]
                else:
                    next_data[sn] = {}

        if failed == len(self.sns) and not any(next_data.values()):
            raise UpdateFailed("All selected devices failed to update")

        return next_data
