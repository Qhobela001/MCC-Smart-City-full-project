from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from macrovideo.gateway.control import CameraGatewayControlServer


def test_gateway_routes_ptz_to_selected_worker() -> None:
    previous = {
        name: os.environ.get(name)
        for name in (
            "CAMERA_GATEWAY_SHARED_KEY",
            "CAMERA_GATEWAY_CONTROL_HOST",
            "CAMERA_GATEWAY_CONTROL_PORT",
        )
    }
    os.environ["CAMERA_GATEWAY_SHARED_KEY"] = "test-shared-key"
    received: list[tuple[str, str, str]] = []

    def provider(identifier: str, direction: str, head: str) -> dict[str, object]:
        received.append((identifier, direction, head))
        return {
            "success": True,
            "camera_identifier": identifier,
            "direction": direction,
            "head": head,
            "message": "PTZ command sent.",
        }

    os.environ["CAMERA_GATEWAY_CONTROL_HOST"] = "127.0.0.1"
    os.environ["CAMERA_GATEWAY_CONTROL_PORT"] = "0"
    server = CameraGatewayControlServer(ptz_provider=provider)
    server.start()
    host, port = server.server.server_address

    try:
        request = Request(
            f"http://{host}:{port}/v1/cameras/MCC-CAM-001/ptz",
            data=json.dumps({"direction": "left", "head": "left"}).encode("utf-8"),
            headers={
                "X-Camera-Gateway-Key": "test-shared-key",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["success"] is True
        assert received == [("MCC-CAM-001", "left", "left")]
    finally:
        server.stop()
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
