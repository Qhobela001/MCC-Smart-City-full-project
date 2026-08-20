from __future__ import annotations

import os

import httpx

from macrovideo.gateway.models import GatewayCameraConfig


class CameraRegistryError(RuntimeError):
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
