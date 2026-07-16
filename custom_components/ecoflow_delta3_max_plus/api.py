"""EcoFlow Cloud API client for Delta 3 Max Plus integration."""

from __future__ import annotations

import hashlib
import hmac
import logging
import random
import time
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import API_HOSTS, DEVICE_LIST_ENDPOINT_CANDIDATES

_LOGGER = logging.getLogger(__name__)


class EcoFlowApiError(Exception):
    """Base error for EcoFlow API failures."""


class EcoFlowAuthError(EcoFlowApiError):
    """Auth error for EcoFlow API failures."""


class EcoFlowApiClient:
    """Low-level API client that signs requests as required by EcoFlow."""

    def __init__(self, session: ClientSession, access_key: str, secret_key: str) -> None:
        self._session = session
        self._access_key = access_key.strip()
        self._secret_key = secret_key.strip()
        self._active_host: str | None = None

    @staticmethod
    def _process_value(prefix: str, value: Any, output: list[str]) -> None:
        if value is None:
            return

        if isinstance(value, list):
            for index, item in enumerate(value):
                EcoFlowApiClient._process_value(f"{prefix}[{index}]", item, output)
            return

        if isinstance(value, dict):
            for key, item in value.items():
                EcoFlowApiClient._process_value(f"{prefix}.{key}", item, output)
            return

        output.append(f"{prefix}={value}")

    @classmethod
    def _generate_query_params(cls, data: dict[str, Any] | None) -> str:
        if not data:
            return ""

        parts: list[str] = []
        for key, value in data.items():
            cls._process_value(key, value, parts)

        parts.sort()
        return "&".join(parts)

    @staticmethod
    def _generate_sign(
        query_string: str,
        access_key: str,
        nonce: str,
        timestamp: str,
        secret_key: str,
    ) -> str:
        target = f"accessKey={access_key}&nonce={nonce}&timestamp={timestamp}"
        if query_string:
            target = f"{query_string}&{target}"

        return hmac.new(secret_key.encode("utf-8"), target.encode("utf-8"), hashlib.sha256).hexdigest()

    def _build_signed_headers(self, query_string: str) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce = str(random.randint(10000, 999999))
        sign = self._generate_sign(query_string, self._access_key, nonce, timestamp, self._secret_key)

        return {
            "accessKey": self._access_key,
            "nonce": nonce,
            "timestamp": timestamp,
            "sign": sign,
        }

    async def _parse_response_data(self, response) -> dict[str, Any]:
        text = await response.text()
        try:
            return await response.json(content_type=None)
        except ValueError:
            return {
                "code": str(response.status),
                "message": "Non-JSON response from EcoFlow API",
                "raw": text,
            }

    async def _request_get(
        self,
        host: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_params = {
            key: str(value)
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        query_string = self._generate_query_params(clean_params)
        headers = self._build_signed_headers(query_string)
        url = f"https://{host}/iot-open/sign{endpoint}{'?' + query_string if query_string else ''}"

        try:
            response = await self._session.get(url, headers=headers)
        except ClientError as err:
            raise EcoFlowApiError(f"GET {endpoint} failed on host {host}: {err}") from err

        data = await self._parse_response_data(response)
        return {"host": host, "url": url, "data": data}

    async def _request_put(
        self,
        host: str,
        endpoint: str,
        body: dict[str, Any],
        *,
        sign_from_body: bool = True,
        include_query: bool = True,
    ) -> dict[str, Any]:
        query_from_body = self._generate_query_params(body)
        sign_query = query_from_body if sign_from_body else ""
        url_query = query_from_body if include_query else ""
        headers = self._build_signed_headers(sign_query)
        url = f"https://{host}/iot-open/sign{endpoint}{'?' + url_query if url_query else ''}"

        try:
            response = await self._session.put(
                url,
                headers={
                    **headers,
                    "Content-Type": "application/json;charset=UTF-8",
                },
                json=body,
            )
        except ClientError as err:
            raise EcoFlowApiError(f"PUT {endpoint} failed on host {host}: {err}") from err

        data = await self._parse_response_data(response)
        return {"host": host, "url": url, "data": data, "requestBody": body}

    async def _request_post(
        self,
        host: str,
        endpoint: str,
        body: dict[str, Any],
        *,
        sign_from_body: bool = True,
        include_query: bool = True,
    ) -> dict[str, Any]:
        query_from_body = self._generate_query_params(body)
        sign_query = query_from_body if sign_from_body else ""
        url_query = query_from_body if include_query else ""
        headers = self._build_signed_headers(sign_query)
        url = f"https://{host}/iot-open/sign{endpoint}{'?' + url_query if url_query else ''}"

        try:
            response = await self._session.post(
                url,
                headers={
                    **headers,
                    "Content-Type": "application/json;charset=UTF-8",
                },
                json=body,
            )
        except ClientError as err:
            raise EcoFlowApiError(f"POST {endpoint} failed on host {host}: {err}") from err

        data = await self._parse_response_data(response)
        return {"host": host, "url": url, "data": data, "requestBody": body}

    @staticmethod
    def _is_success(data: dict[str, Any] | None) -> bool:
        return bool(data and str(data.get("code")) == "0")

    @staticmethod
    def _is_auth_error(data: dict[str, Any] | None) -> bool:
        if not data:
            return False
        code = str(data.get("code", "")).strip()
        message = str(data.get("message", "")).lower()
        return code in {"1001", "1002", "401", "403"} or "auth" in message or "access" in message

    def _hosts_to_try(self) -> list[str]:
        if not self._active_host:
            return list(API_HOSTS)

        return [self._active_host, *[host for host in API_HOSTS if host != self._active_host]]

    async def async_list_account_devices_raw(self) -> dict[str, Any]:
        last_error: dict[str, Any] | None = None

        for host in self._hosts_to_try():
            for endpoint, params in DEVICE_LIST_ENDPOINT_CANDIDATES:
                result = await self._request_get(host, endpoint, params)
                data = result.get("data")

                if self._is_success(data):
                    self._active_host = host
                    return result

                if self._is_auth_error(data):
                    raise EcoFlowAuthError(str(data))

                last_error = result

        raise EcoFlowApiError(f"Failed to list EcoFlow devices: {last_error}")

    async def async_get_device_params_raw(self, sn: str) -> dict[str, Any]:
        last_error: dict[str, Any] | None = None

        for host in self._hosts_to_try():
            result = await self._request_get(host, "/device/quota/all", {"sn": sn})
            data = result.get("data")

            if self._is_success(data):
                self._active_host = host
                return result

            if self._is_auth_error(data):
                raise EcoFlowAuthError(str(data))

            last_error = result

        raise EcoFlowApiError(f"Failed to fetch telemetry for SN {sn}: {last_error}")

    async def async_set_ac_outlet_power(self, sn: str, ac_index: int, state: bool) -> bool:
        if not self._active_host:
            await self.async_get_device_params_raw(sn)

        payload = self.build_ac_power_payload(sn, ac_index, state)
        last_error: dict[str, Any] | None = None
        last_auth_data: dict[str, Any] | None = None

        variants = (
            ("put", True, True),
            ("put", False, False),
            ("post", False, False),
            ("post", True, True),
        )

        for host in self._hosts_to_try():
            for method, sign_from_body, include_query in variants:
                if method == "post":
                    result = await self._request_post(
                        host,
                        "/device/quota",
                        payload,
                        sign_from_body=sign_from_body,
                        include_query=include_query,
                    )
                else:
                    result = await self._request_put(
                        host,
                        "/device/quota",
                        payload,
                        sign_from_body=sign_from_body,
                        include_query=include_query,
                    )

                data = result.get("data")

                if self._is_success(data):
                    self._active_host = host
                    return True

                if self._is_auth_error(data):
                    last_auth_data = data

                last_error = result

        _LOGGER.error("Failed AC command for SN %s, AC%d, state %s: %s", sn, ac_index, state, last_error)
        if last_auth_data is not None:
            raise EcoFlowAuthError(str(last_auth_data))
        return False

    @staticmethod
    def build_ac_power_payload(sn: str, ac_index: int, state: bool) -> dict[str, Any]:
        params = {"cfgAc2OutOpen": bool(state)} if ac_index == 2 else {"cfgAcOutOpen": bool(state)}
        return {
            "sn": sn,
            "cmdId": 17,
            "cmdFunc": 254,
            "dest": 2,
            "dirDest": 1,
            "dirSrc": 1,
            "needAck": True,
            "params": params,
        }

    @staticmethod
    def map_devices_response(data: dict[str, Any]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()

        def collect(node: Any) -> None:
            if node is None:
                return

            if isinstance(node, list):
                for item in node:
                    collect(item)
                return

            if not isinstance(node, dict):
                return

            sn = node.get("sn") or node.get("deviceSn") or node.get("serialNumber") or node.get("serialNo")
            if sn:
                entry = {
                    "sn": str(sn),
                    "deviceName": node.get("deviceName") or node.get("name"),
                    "productName": node.get("productName") or node.get("productType"),
                    "online": node.get("online", node.get("isOnline")),
                }
                marker = repr(entry)
                if marker not in seen:
                    seen.add(marker)
                    output.append(entry)

            for value in node.values():
                if isinstance(value, (dict, list)):
                    collect(value)

        collect(data)
        return output

    @staticmethod
    def _as_positive_number(value: Any) -> float:
        try:
            numeric = float(value or 0)
        except (TypeError, ValueError):
            return 0
        return abs(numeric)

    @staticmethod
    def _format_seconds_hhmmss(value: Any) -> str | None:
        try:
            total_seconds = int(value)
        except (TypeError, ValueError):
            return None

        if total_seconds < 0:
            return None

        hours = str(total_seconds // 3600).zfill(2)
        minutes = str((total_seconds % 3600) // 60).zfill(2)
        seconds = str(total_seconds % 60).zfill(2)
        return f"{hours}:{minutes}:{seconds}"

    @staticmethod
    def _map_chg_dsg_state_description(value: Any) -> str | None:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None

        if numeric == 0:
            return "Idle"
        if numeric == 1:
            return "discharging"
        if numeric == 2:
            return "charging"
        return None

    @staticmethod
    def _as_bool_or_none(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "on", "yes"}:
                return True
            if normalized in {"0", "false", "off", "no"}:
                return False
        return None

    @classmethod
    def map_data_to_api_response(cls, raw_data: dict[str, Any]) -> dict[str, Any]:
        ac_out_items = raw_data.get("powGetAcOutList.powGetAcOutItem", [])
        item1 = ac_out_items[0] if isinstance(ac_out_items, list) and len(ac_out_items) > 0 else 0
        item3 = ac_out_items[2] if isinstance(ac_out_items, list) and len(ac_out_items) > 2 else 0

        cms_dsg_rem_time = float(raw_data.get("cmsDsgRemTime") or 0)
        cms_chg_dsg_state = float(raw_data.get("cmsChgDsgState") or 0)

        return {
            "powGetAcIn": float(raw_data.get("powGetAcIn") or 0),
            "batteryperc": float(raw_data.get("cmsBattSoc") or 0),
            "poweroutsum": float(raw_data.get("powOutSumW") or 0),
            "poweroutAc1": cls._as_positive_number(item1),
            "poweroutAc2": cls._as_positive_number(item3),
            "powInSumW": float(raw_data.get("powInSumW") or 0),
            "energyBackupEn": float(raw_data.get("energyBackupEn") or 0),
            "cmsMaxChgSoc": float(raw_data.get("cmsMaxChgSoc") or 0),
            "cmsMinDsgSoc": float(raw_data.get("cmsMinDsgSoc") or 0),
            "powGetTypec3": float(raw_data.get("powGetTypec3") or 0),
            "powGetTypec1": float(raw_data.get("powGetTypec1") or 0),
            "powGetTypec2": float(raw_data.get("powGetTypec2") or 0),
            "PowerUsbTypeC1": cls._as_positive_number(raw_data.get("powGetTypec1")),
            "PowerUsbTypeC2": cls._as_positive_number(raw_data.get("powGetTypec2")),
            "PowerUsbTypeC3": cls._as_positive_number(raw_data.get("powGetTypec3")),
            "cmsDsgRemTime": cms_dsg_rem_time,
            "cmsDsgRemTimeFmt": cls._format_seconds_hhmmss(cms_dsg_rem_time),
            "cmsChgDsgState": cms_chg_dsg_state,
            "cmsChgDsgStateDesc": cls._map_chg_dsg_state_description(cms_chg_dsg_state),
            "cfgAcOutOpen": cls._as_bool_or_none(raw_data.get("cfgAcOutOpen")),
            "cfgAc2OutOpen": cls._as_bool_or_none(raw_data.get("cfgAc2OutOpen")),
        }

    async def async_get_mapped_data(self, sn: str) -> dict[str, Any]:
        result = await self.async_get_device_params_raw(sn)
        raw = result.get("data", {}).get("data", {})
        return self.map_data_to_api_response(raw)
