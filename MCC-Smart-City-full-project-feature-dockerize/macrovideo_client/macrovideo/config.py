from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    DEFAULT_CAMERA_PORT,
    DEFAULT_CONNECT_TIMEOUT,
    QUALITY_SD,
)


@dataclass(frozen=True)
class CameraConfig:
    ip: str
    port: int = DEFAULT_CAMERA_PORT
    username: str = "admin"
    password: str = ""
    device_id: int = 0
    quality: int = QUALITY_SD
    timeout: float = DEFAULT_CONNECT_TIMEOUT

    def __post_init__(self) -> None:
        if not self.ip:
            raise ValueError("Camera IP address cannot be empty.")

        if not 1 <= self.port <= 65535:
            raise ValueError("Camera port must be between 1 and 65535.")

        if self.device_id < 0:
            raise ValueError("Device ID cannot be negative.")

        if self.timeout <= 0:
            raise ValueError("Timeout must be greater than zero.")