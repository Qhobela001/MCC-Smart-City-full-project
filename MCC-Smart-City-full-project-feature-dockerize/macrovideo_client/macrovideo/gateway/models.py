from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayCameraConfig:
    camera_identifier: str
    gateway_path: str
    host: str
    port: int
    device_id: int
    username: str
    password: str
    enabled: bool = True

    @classmethod
    def from_api(cls, payload: dict[str, object]) -> "GatewayCameraConfig":
        return cls(
            camera_identifier=str(payload["camera_identifier"]),
            gateway_path=str(payload["gateway_path"]),
            host=str(payload["host"]),
            port=int(payload.get("port") or 8800),
            device_id=int(payload["device_id"]),
            username=str(payload.get("username") or "admin"),
            password=str(payload.get("password") or ""),
            enabled=bool(payload.get("enabled", True)),
        )
