from __future__ import annotations

import hmac
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import unquote

from macrovideo.protocol.legacy_lan_login import perform_legacy_lan_login


_MAX_REQUEST_BYTES = 8192


class _ControlHandler(BaseHTTPRequestHandler):
    server_version = "MCCCameraGatewayControl/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Do not emit request bodies or credentials into container logs.
        return

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = os.getenv("CAMERA_GATEWAY_SHARED_KEY", "")
        supplied = self.headers.get("X-Camera-Gateway-Key", "")
        return bool(expected) and hmac.compare_digest(supplied, expected)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return

        if self.path != "/v1/health":
            self._write_json(404, {"detail": "Not found."})
            return

        if not self._authorized():
            self._write_json(403, {"detail": "Gateway authentication failed."})
            return

        provider = getattr(self.server, "health_provider", None)
        if provider is None:
            self._write_json(503, {"detail": "Gateway health is unavailable."})
            return

        try:
            payload = provider()
        except Exception:
            self._write_json(503, {"detail": "Gateway health is unavailable."})
            return

        self._write_json(200, payload)

    def do_POST(self) -> None:
        is_test = self.path == "/v1/test-connection"
        ptz_prefix = "/v1/cameras/"
        is_ptz = self.path.startswith(ptz_prefix) and self.path.endswith("/ptz")
        if not is_test and not is_ptz:
            self._write_json(404, {"detail": "Not found."})
            return

        if not self._authorized():
            self._write_json(403, {"detail": "Gateway authentication failed."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        if content_length <= 0 or content_length > _MAX_REQUEST_BYTES:
            self._write_json(400, {"detail": "Invalid request size."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError
        except (TypeError, ValueError, json.JSONDecodeError):
            self._write_json(400, {"detail": "Invalid JSON request."})
            return

        if is_ptz:
            identifier = unquote(self.path[len(ptz_prefix):-len("/ptz")]).strip()
            direction = str(payload.get("direction") or "").strip().lower()
            head = str(payload.get("head") or "main").strip().lower()
            if (not identifier or direction not in {"up", "down", "left", "right"}
                    or head not in {"main", "right", "left"}):
                self._write_json(400, {"detail": "Invalid PTZ request."})
                return

            provider = getattr(self.server, "ptz_provider", None)
            if provider is None:
                self._write_json(503, {"detail": "PTZ control is unavailable."})
                return
            try:
                result = provider(identifier, direction, head)
            except LookupError:
                self._write_json(404, {"detail": "Camera worker was not found."})
                return
            except RuntimeError as exc:
                self._write_json(409, {"detail": str(exc)})
                return
            except OSError:
                self._write_json(502, {"detail": "The camera rejected the PTZ transport."})
                return
            except Exception:
                self._write_json(500, {"detail": "The gateway could not send PTZ control."})
                return

            self._write_json(200, result)
            return

        try:
            host = str(payload["host"]).strip()
            port = int(payload.get("port") or 8800)
            device_id = int(payload["device_id"])
            username = str(payload["username"]).strip()
            password = str(payload["password"])
        except (KeyError, TypeError, ValueError):
            self._write_json(400, {"detail": "Invalid V380 test request."})
            return

        if not host or not username or not password or device_id <= 0:
            self._write_json(400, {"detail": "Incomplete V380 test request."})
            return
        if port < 1 or port > 65535:
            self._write_json(400, {"detail": "Invalid V380 port."})
            return

        try:
            exchange = perform_legacy_lan_login(
                host=host,
                port=port,
                device_id=device_id,
                username=username,
                password=password,
            )
            login = exchange.response
        except (TimeoutError, socket.timeout):
            self._write_json(
                200,
                {
                    "success": False,
                    "outcome": "timeout",
                    "login_result": None,
                    "message": (
                        "The camera did not return a V380 LAN login response "
                        "before the timeout."
                    ),
                },
            )
            return
        except OSError:
            self._write_json(
                200,
                {
                    "success": False,
                    "outcome": "unreachable",
                    "login_result": None,
                    "message": "The camera could not be reached on the V380 LAN port.",
                },
            )
            return
        except Exception:
            self._write_json(
                200,
                {
                    "success": False,
                    "outcome": "gateway_error",
                    "login_result": None,
                    "message": "The gateway could not complete the V380 login test.",
                },
            )
            return

        result = int(login.login_result)
        if login.succeeded:
            self._write_json(
                200,
                {
                    "success": True,
                    "outcome": "authenticated",
                    "login_result": result,
                    "message": "V380 LAN authentication succeeded.",
                },
            )
            return

        self._write_json(
            200,
            {
                "success": False,
                "outcome": "rejected",
                "login_result": result,
                "message": (
                    f"The camera rejected the V380 LAN login (result {result}). "
                    "Verify the device username and password in the V380 app."
                ),
            },
        )


class CameraGatewayControlServer:
    def __init__(
        self,
        *,
        health_provider: Callable[[], dict[str, Any]] | None = None,
        ptz_provider: Callable[[str, str, str], dict[str, Any]] | None = None,
    ) -> None:
        host = os.getenv("CAMERA_GATEWAY_CONTROL_HOST", "0.0.0.0").strip()
        port = int(os.getenv("CAMERA_GATEWAY_CONTROL_PORT", "8090"))
        self.address = (host, port)
        self.server = ThreadingHTTPServer(self.address, _ControlHandler)
        self.server.health_provider = health_provider  # type: ignore[attr-defined]
        self.server.ptz_provider = ptz_provider  # type: ignore[attr-defined]
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            name="camera-gateway-control",
            daemon=True,
        )

    def start(self) -> None:
        self.thread.start()
        print(
            f"[GATEWAY] control API listening on {self.address[0]}:{self.address[1]}.",
            flush=True,
        )

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
