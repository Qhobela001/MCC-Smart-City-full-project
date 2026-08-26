from __future__ import annotations

import os
from urllib.parse import quote

import httpx

from macrovideo.gateway.models import GatewayCameraConfig


class CameraRegistryError(RuntimeError):
    pass


class CameraStatusReportError(RuntimeError):
    pass


class MCCCameraRegistry:
    def __init__(
        self,
        *,
        url: str | None = None,
        shared_key: str | None = None,
        timeout: float = 8.0,
    ) -> None:
        self.url = (
            url
            or os.getenv(
                "MCC_CAMERA_REGISTRY_URL",
                "http://backend:8000/api/v1/live-streams/gateway/cameras",
            )
        ).strip()
        self.shared_key = (
            shared_key
            if shared_key is not None
            else os.getenv("CAMERA_GATEWAY_SHARED_KEY", "")
        )
        self.timeout = timeout

        if not self.url:
            raise ValueError("MCC camera registry URL cannot be empty.")
        if not self.shared_key:
            raise ValueError(
                "CAMERA_GATEWAY_SHARED_KEY must be configured."
            )

    def fetch(self) -> list[GatewayCameraConfig]:
        try:
            response = httpx.get(
                self.url,
                headers={
                    "X-Camera-Gateway-Key": self.shared_key,
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise CameraRegistryError(
                f"Unable to load MCC camera registry: {exc}"
            ) from exc

        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list):
            raise CameraRegistryError(
                "MCC camera registry returned an invalid items value."
            )

        items: list[GatewayCameraConfig] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            try:
                item = GatewayCameraConfig.from_api(raw_item)
            except (KeyError, TypeError, ValueError):
                continue
            if item.enabled:
                items.append(item)

        return items


class MCCCameraStatusReporter:
    def __init__(
        self,
        *,
        url_template: str | None = None,
        shared_key: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.url_template = (
            url_template
            or os.getenv(
                "MCC_CAMERA_HEARTBEAT_URL_TEMPLATE",
                (
                    "http://backend:8000/api/v1/cameras/gateway/"
                    "{camera_identifier}/heartbeat"
                ),
            )
        ).strip()
        self.shared_key = (
            shared_key
            if shared_key is not None
            else os.getenv("CAMERA_GATEWAY_SHARED_KEY", "")
        )
        self.timeout = timeout

        if "{camera_identifier}" not in self.url_template:
            raise ValueError(
                "MCC_CAMERA_HEARTBEAT_URL_TEMPLATE must contain "
                "{camera_identifier}."
            )
        if not self.shared_key:
            raise ValueError(
                "CAMERA_GATEWAY_SHARED_KEY must be configured."
            )

    def report(
        self,
        *,
        camera_identifier: str,
        status: str,
        stream_status: str,
    ) -> None:
        url = self.url_template.format(
            camera_identifier=quote(camera_identifier, safe=""),
        )
        try:
            response = httpx.post(
                url,
                headers={
                    "X-Camera-Gateway-Key": self.shared_key,
                    "Accept": "application/json",
                },
                json={
                    "status": status,
                    "stream_status": stream_status,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CameraStatusReportError(
                f"Unable to report camera status: {exc}"
            ) from exc
