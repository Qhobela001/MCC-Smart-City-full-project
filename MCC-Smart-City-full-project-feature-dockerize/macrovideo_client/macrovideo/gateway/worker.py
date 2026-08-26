from __future__ import annotations

import os
import threading
import time

import av

from macrovideo.gateway.health import (
    CameraHealthTracker,
    classify_worker_failure,
)
from macrovideo.gateway.models import GatewayCameraConfig
from macrovideo.gateway.publisher import FFmpegPublisher
from macrovideo.protocol.legacy_lan_login import (
    perform_legacy_lan_login,
)
from macrovideo.protocol.legacy_live_client import (
    LegacyV2LiveClient,
)
from macrovideo.protocol.legacy_live_stream import LegacyLiveSession


class CameraWorker(threading.Thread):
    def __init__(
        self,
        config: GatewayCameraConfig,
        *,
        retry_seconds: float | None = None,
    ) -> None:
        super().__init__(
            name=f"camera-{config.camera_identifier}",
            daemon=True,
        )
        self.config = config
        self.retry_seconds = (
            retry_seconds
            if retry_seconds is not None
            else float(os.getenv("CAMERA_RECONNECT_SECONDS", "5"))
        )
        self.stop_event = threading.Event()
        self.stopped_event = threading.Event()
        self._resource_lock = threading.Lock()
        self._active_client: LegacyV2LiveClient | None = None
        self._active_publisher: FFmpegPublisher | None = None
        degraded_after_seconds = float(
            os.getenv("CAMERA_DEGRADED_AFTER_SECONDS", "15")
        )
        offline_after_seconds = float(
            os.getenv("CAMERA_OFFLINE_AFTER_SECONDS", "60")
        )
        self.health = CameraHealthTracker(
            degraded_after_seconds=degraded_after_seconds,
            offline_after_seconds=offline_after_seconds,
        )

    def stop(self) -> None:
        self.stop_event.set()
        with self._resource_lock:
            client = self._active_client
            publisher = self._active_publisher

        # Closing active resources interrupts blocking media reads and ffmpeg
        # writes so a targeted stop does not wait for the normal idle timeout.
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                print(
                    f"[WORKER:{self.config.camera_identifier}] "
                    f"client close warning: {type(exc).__name__}.",
                    flush=True,
                )
        if publisher is not None:
            try:
                publisher.close()
            except Exception as exc:
                print(
                    f"[WORKER:{self.config.camera_identifier}] "
                    f"publisher close warning: {type(exc).__name__}.",
                    flush=True,
                )

    def _set_active_client(
        self,
        client: LegacyV2LiveClient | None,
    ) -> None:
        with self._resource_lock:
            self._active_client = client

    def _set_active_publisher(
        self,
        publisher: FFmpegPublisher | None,
    ) -> None:
        with self._resource_lock:
            self._active_publisher = publisher

    def run(self) -> None:
        print(
            f"[WORKER:{self.config.camera_identifier}] "
            f"started for {self.config.host}:{self.config.port} "
            f"(device {self.config.device_id}).",
            flush=True,
        )

        while not self.stop_event.is_set():
            client: LegacyV2LiveClient | None = None
            publisher: FFmpegPublisher | None = None

            try:
                self.health.mark_connecting()
                login_exchange = perform_legacy_lan_login(
                    host=self.config.host,
                    port=self.config.port,
                    device_id=self.config.device_id,
                    username=self.config.username,
                    password=self.config.password,
                )
                login = login_exchange.response

                if not login.succeeded:
                    raise PermissionError(
                        f"LAN login rejected with result "
                        f"{login.login_result}."
                    )

                session = LegacyLiveSession(
                    device_id=self.config.device_id,
                    login_handle=login.handle,
                    token_session=login.token_session,
                    protocol_version=login.protocol_version,
                )

                client = LegacyV2LiveClient(
                    host=self.config.host,
                    port=self.config.port,
                    session=session,
                    socket_timeout=float(
                        os.getenv("V380_LIVE_SOCKET_TIMEOUT", "2")
                    ),
                    idle_timeout=float(
                        os.getenv("V380_LIVE_IDLE_TIMEOUT", "20")
                    ),
                )
                self._set_active_client(client)
                start_response = client.connect()

                print(
                    f"[WORKER:{self.config.camera_identifier}] "
                    f"camera stream active; login handle={login.handle}.",
                    flush=True,
                )

                decoder = av.CodecContext.create("hevc", "r")
                fallback_fps = float(
                    os.getenv("V380_DEFAULT_FPS", "12")
                )
                published = 0
                started_at = time.monotonic()
                last_report = started_at

                for source_frame, hevc_payload in client.iter_hevc_payloads():
                    if self.stop_event.is_set():
                        break

                    for packet in decoder.parse(hevc_payload):
                        for decoded in decoder.decode(packet):
                            if self.stop_event.is_set():
                                break

                            image = decoded.to_ndarray(format="bgr24")
                            height, width = image.shape[:2]

                            if publisher is None:
                                fps = float(
                                    source_frame.frame_rate
                                    if source_frame.frame_rate > 0
                                    else fallback_fps
                                )
                                publisher = FFmpegPublisher(
                                    gateway_path=self.config.gateway_path,
                                    width=width,
                                    height=height,
                                    fps=fps,
                                )
                                publisher.start()
                                self._set_active_publisher(publisher)

                            if self.stop_event.is_set():
                                break

                            publisher.write_bgr(image.tobytes())
                            published += 1
                            self.health.mark_published()

                            now = time.monotonic()
                            if now - last_report >= 10:
                                elapsed = max(now - started_at, 0.001)
                                print(
                                    f"[WORKER:{self.config.camera_identifier}] "
                                    f"publishing; frames={published}, "
                                    f"avg_fps={published / elapsed:.1f}.",
                                    flush=True,
                                )
                                last_report = now

                if self.stop_event.is_set():
                    break

                raise ConnectionError(
                    "V380 live-media iterator ended unexpectedly."
                )

            except Exception as exc:
                if not self.stop_event.is_set():
                    failure = classify_worker_failure(exc)
                    self.health.mark_retrying(failure)
                    print(
                        f"[WORKER:{self.config.camera_identifier}] "
                        f"failure={failure.code}: {failure.message}",
                        flush=True,
                    )

            finally:
                if publisher is not None:
                    publisher.close()
                    self._set_active_publisher(None)
                if client is not None:
                    client.close()
                    self._set_active_client(None)

            if not self.stop_event.is_set():
                print(
                    f"[WORKER:{self.config.camera_identifier}] "
                    f"retrying in {self.retry_seconds:.1f}s.",
                    flush=True,
                )
                self.stop_event.wait(self.retry_seconds)

        self.health.mark_stopped()
        self.stopped_event.set()
        print(
            f"[WORKER:{self.config.camera_identifier}] stopped.",
            flush=True,
        )
