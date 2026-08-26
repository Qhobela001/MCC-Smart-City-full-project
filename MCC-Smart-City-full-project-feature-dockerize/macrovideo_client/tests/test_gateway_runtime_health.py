from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from macrovideo.gateway.control import CameraGatewayControlServer


def test_detailed_health_requires_shared_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMERA_GATEWAY_SHARED_KEY", "test-shared-key")
    monkeypatch.setenv("CAMERA_GATEWAY_CONTROL_HOST", "127.0.0.1")
    monkeypatch.setenv("CAMERA_GATEWAY_CONTROL_PORT", "0")
    server = CameraGatewayControlServer(
        health_provider=lambda: {"available": True, "status": "online"},
    )
    server.start()
    host, port = server.server.server_address

    try:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://{host}:{port}/v1/health", timeout=2)
        assert error.value.code == 403

        request = Request(
            f"http://{host}:{port}/v1/health",
            headers={"X-Camera-Gateway-Key": "test-shared-key"},
        )
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload == {"available": True, "status": "online"}
    finally:
        server.stop()
