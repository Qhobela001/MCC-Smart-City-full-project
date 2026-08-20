from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from fractions import Fraction
from urllib.parse import quote, urlsplit, urlunsplit

from macrovideo.protocol.legacy_lan_login import perform_legacy_lan_login
from macrovideo.protocol.legacy_live_client import LegacyV2LiveClient
from macrovideo.protocol.legacy_live_stream import LegacyLiveSession


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer; received {raw!r}.") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric; received {raw!r}.") from exc


def normalize_gateway_path(camera_identifier: str) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        camera_identifier.strip().lower(),
    ).strip("-")
    if not normalized:
        raise ValueError("MCC camera identifier produces an empty MediaMTX path.")
    return normalized


@dataclass(frozen=True)
class GatewayConfig:
    camera_host: str
    camera_port: int
    device_id: int
    camera_username: str
    camera_password: str
    camera_identifier: str
    mediamtx_rtsp_base_url: str
    publisher_username: str
    publisher_password: str
    output_fps: int = 12
    output_bitrate: int = 1_500_000
    socket_timeout: float = 2.0
    idle_timeout: float = 20.0
    reconnect_delay: float = 2.0
    report_interval: float = 5.0
    encoder: str = ""

    @property
    def gateway_path(self) -> str:
        return normalize_gateway_path(self.camera_identifier)

    @classmethod
    def from_environment(cls) -> "GatewayConfig":
        device_id = _env_int("V380_DEVICE_ID", 105848032)
        camera_identifier = os.getenv(
            "MCC_CAMERA_IDENTIFIER",
            str(device_id),
        ).strip()

        config = cls(
            camera_host=os.getenv("V380_CAMERA_HOST", "192.168.1.30").strip(),
            camera_port=_env_int("V380_CAMERA_PORT", 8800),
            device_id=device_id,
            camera_username=os.getenv("V380_CAMERA_USERNAME", "admin").strip(),
            camera_password=os.getenv("V380_CAMERA_PASSWORD", ""),
            camera_identifier=camera_identifier,
            mediamtx_rtsp_base_url=os.getenv(
                "MEDIAMTX_RTSP_BASE_URL",
                "rtsp://127.0.0.1:8554",
            ).strip(),
            publisher_username=os.getenv(
                "LIVE_STREAM_PUBLISH_USERNAME",
                "mcc-v380-publisher",
            ),
            publisher_password=os.getenv(
                "LIVE_STREAM_PUBLISH_PASSWORD",
                "ChangeThisPublisherPassword!",
            ),
            output_fps=max(1, _env_int("MCC_STREAM_FPS", 12)),
            output_bitrate=max(100_000, _env_int("MCC_STREAM_BITRATE", 1_500_000)),
            socket_timeout=max(0.25, _env_float("V380_LIVE_SOCKET_TIMEOUT", 2.0)),
            idle_timeout=max(2.0, _env_float("V380_LIVE_IDLE_TIMEOUT", 20.0)),
            reconnect_delay=max(0.25, _env_float("V380_LIVE_RECONNECT_DELAY", 2.0)),
            report_interval=max(1.0, _env_float("MCC_GATEWAY_REPORT_INTERVAL", 5.0)),
            encoder=os.getenv("MCC_H264_ENCODER", "").strip(),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.camera_host:
            raise ValueError("V380_CAMERA_HOST cannot be empty.")
        if not 1 <= self.camera_port <= 65535:
            raise ValueError("V380_CAMERA_PORT must be between 1 and 65535.")
        if self.device_id <= 0:
            raise ValueError("V380_DEVICE_ID must be positive.")
        if not self.camera_username:
            raise ValueError("V380_CAMERA_USERNAME cannot be empty.")
        if not self.camera_password:
            raise ValueError(
                "V380_CAMERA_PASSWORD is required by the current legacy LAN login implementation."
            )
        if not self.camera_identifier:
            raise ValueError("MCC_CAMERA_IDENTIFIER cannot be empty.")
        normalize_gateway_path(self.camera_identifier)
        if not self.mediamtx_rtsp_base_url.startswith(("rtsp://", "rtsps://")):
            raise ValueError("MEDIAMTX_RTSP_BASE_URL must be an RTSP/RTSPS URL.")
        if not self.publisher_username or not self.publisher_password:
            raise ValueError("MediaMTX publisher username/password cannot be empty.")


class MediaMTXH264Publisher:
    """Decode-ready VideoFrames -> browser-compatible H.264 -> MediaMTX RTSP."""

    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self._container = None
        self._stream = None
        self._frame_index = 0
        self._encoder_name: str | None = None
        self._time_base = Fraction(1, self.config.output_fps)

    @property
    def publish_url(self) -> str:
        parsed = urlsplit(self.config.mediamtx_rtsp_base_url.rstrip("/"))
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port
        authority = f"{quote(self.config.publisher_username, safe='')}:{quote(self.config.publisher_password, safe='')}@{host}"
        if port is not None:
            authority += f":{port}"
        path = f"{parsed.path.rstrip('/')}/{self.config.gateway_path}"
        return urlunsplit((parsed.scheme, authority, path, "", ""))

    @property
    def safe_publish_url(self) -> str:
        parsed = urlsplit(self.config.mediamtx_rtsp_base_url.rstrip("/"))
        host = parsed.hostname or "127.0.0.1"
        authority = host
        if parsed.port is not None:
            authority += f":{parsed.port}"
        path = f"{parsed.path.rstrip('/')}/{self.config.gateway_path}"
        return urlunsplit((parsed.scheme, authority, path, "", ""))

    @staticmethod
    def _choose_encoder(av_module, requested: str) -> str:
        candidates: list[str] = []
        if requested:
            candidates.append(requested)
        candidates.extend(["libx264", "h264_nvenc", "h264_mf", "h264"])

        seen: set[str] = set()
        failures: list[str] = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            try:
                av_module.Codec(candidate, "w")
                return candidate
            except Exception as exc:
                failures.append(f"{candidate}: {exc}")

        raise RuntimeError(
            "No H.264 encoder is available in this PyAV/FFmpeg build. Tried: "
            + "; ".join(failures)
        )

    def start(self, video_frame) -> None:
        if self._container is not None:
            return

        import av

        self._encoder_name = self._choose_encoder(av, self.config.encoder)
        print(f"[GATEWAY] H.264 encoder: {self._encoder_name}")
        print(f"[GATEWAY] Publishing to: {self.safe_publish_url}")

        container = av.open(
            self.publish_url,
            mode="w",
            format="rtsp",
            options={
                "rtsp_transport": "tcp",
                "muxdelay": "0.0",
            },
        )

        stream = container.add_stream(
            self._encoder_name,
            rate=self.config.output_fps,
        )
        stream.width = video_frame.width
        stream.height = video_frame.height
        stream.pix_fmt = "yuv420p"
        stream.bit_rate = self.config.output_bitrate
        stream.time_base = self._time_base
        stream.codec_context.time_base = self._time_base
        stream.codec_context.gop_size = max(self.config.output_fps, 12)
        stream.codec_context.max_b_frames = 0

        if self._encoder_name == "libx264":
            stream.options = {
                "preset": "ultrafast",
                "tune": "zerolatency",
                "profile": "baseline",
            }
        elif self._encoder_name == "h264_nvenc":
            stream.options = {
                "preset": "p1",
                "tune": "ull",
                "zerolatency": "1",
            }

        self._container = container
        self._stream = stream
        print(
            "[GATEWAY] MediaMTX publisher ready: "
            f"{video_frame.width}x{video_frame.height} @ {self.config.output_fps} FPS"
        )

    def write(self, video_frame) -> int:
        if self._container is None:
            self.start(video_frame)

        assert self._container is not None
        assert self._stream is not None

        frame = video_frame.reformat(
            width=self._stream.width,
            height=self._stream.height,
            format="yuv420p",
        )
        frame.pts = self._frame_index
        frame.time_base = self._time_base
        self._frame_index += 1

        packets = self._stream.encode(frame)
        count = 0
        for packet in packets:
            self._container.mux(packet)
            count += 1
        return count

    def close(self) -> None:
        container = self._container
        stream = self._stream
        self._container = None
        self._stream = None

        if container is None:
            return

        if stream is not None:
            try:
                for packet in stream.encode(None):
                    container.mux(packet)
            except Exception:
                pass

        try:
            container.close()
        except Exception:
            pass


class V380MCCGateway:
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.total_camera_connections = 0
        self.total_reconnects = 0
        self.total_decoded_frames = 0
        self.total_published_frames = 0

    def _open_camera(self) -> LegacyV2LiveClient:
        login_exchange = perform_legacy_lan_login(
            host=self.config.camera_host,
            port=self.config.camera_port,
            device_id=self.config.device_id,
            username=self.config.camera_username,
            password=self.config.camera_password,
        )
        login = login_exchange.response
        if not login.succeeded:
            raise PermissionError(
                f"Camera rejected LAN login with result {login.login_result}."
            )

        session = LegacyLiveSession(
            device_id=self.config.device_id,
            login_handle=login.handle,
            token_session=login.token_session,
            protocol_version=login.protocol_version,
        )
        client = LegacyV2LiveClient(
            host=self.config.camera_host,
            port=self.config.camera_port,
            session=session,
            socket_timeout=self.config.socket_timeout,
            idle_timeout=self.config.idle_timeout,
        )
        response = client.connect()
        self.total_camera_connections += 1
        print(
            "[GATEWAY] V380 live session active: "
            f"handle={login.handle}, camera={response.width}x{response.height}"
        )
        return client

    def run_forever(self) -> int:
        import av

        print("=" * 72)
        print("V380 -> MCC MEDIAMTX LIVE GATEWAY")
        print("=" * 72)
        print(f"Camera: {self.config.camera_host}:{self.config.camera_port}")
        print(f"V380 device ID: {self.config.device_id}")
        print(f"MCC camera identifier: {self.config.camera_identifier}")
        print(f"MediaMTX path: {self.config.gateway_path}")
        print("Output: H.264 baseline/zero-B-frame RTSP for browser WebRTC compatibility")
        print("Press Ctrl+C to stop.\n")

        while True:
            client: LegacyV2LiveClient | None = None
            publisher: MediaMTXH264Publisher | None = None
            try:
                client = self._open_camera()
                publisher = MediaMTXH264Publisher(self.config)
                decoder = av.CodecContext.create("hevc", "r")
                session_decoded = 0
                session_published = 0
                session_start = time.monotonic()
                last_report = session_start

                for _, hevc_payload in client.iter_hevc_payloads():
                    for packet in decoder.parse(hevc_payload):
                        for video_frame in decoder.decode(packet):
                            session_decoded += 1
                            self.total_decoded_frames += 1
                            publisher.write(video_frame)
                            session_published += 1
                            self.total_published_frames += 1

                    now = time.monotonic()
                    if now - last_report >= self.config.report_interval:
                        elapsed = max(now - session_start, 0.001)
                        stats = client.stats
                        print(
                            "[GATEWAY] "
                            f"published={session_published}, "
                            f"decoded={session_decoded}, "
                            f"fps={session_published / elapsed:.1f}, "
                            f"v380_frames={stats.complete_frames}, "
                            f"transport={stats.transport_fragments}"
                        )
                        last_report = now

            except KeyboardInterrupt:
                print("\n[GATEWAY] Stop requested by user.")
                return 0
            except PermissionError as exc:
                print(f"[GATEWAY] Authentication failed: {exc}")
                print(
                    "[GATEWAY] Verify V380_CAMERA_PASSWORD. "
                    f"Retrying in {self.config.reconnect_delay:.1f}s."
                )
                self.total_reconnects += 1
            except Exception as exc:
                print(
                    "[GATEWAY] Session/publisher lost: "
                    f"{type(exc).__name__}: {exc}"
                )
                print(
                    "[GATEWAY] A fresh camera login and MediaMTX publisher "
                    f"will be opened in {self.config.reconnect_delay:.1f}s."
                )
                self.total_reconnects += 1
            finally:
                if publisher is not None:
                    publisher.close()
                if client is not None:
                    client.close()

            time.sleep(self.config.reconnect_delay)


def run_gateway(config: GatewayConfig | None = None) -> int:
    return V380MCCGateway(config or GatewayConfig.from_environment()).run_forever()
