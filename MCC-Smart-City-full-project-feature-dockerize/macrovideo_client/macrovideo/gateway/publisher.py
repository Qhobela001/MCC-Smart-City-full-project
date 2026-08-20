from __future__ import annotations

import os
import subprocess
from urllib.parse import quote


class FFmpegPublisher:
    """
    Publish decoded BGR frames to MediaMTX as browser-compatible H.264.

    ffmpeg is intentionally a child process rather than another Python
    media stack. This gives us a predictable H.264/RTSP boundary and lets
    Docker restart the whole gateway if the media toolchain itself fails.
    """

    def __init__(
        self,
        *,
        gateway_path: str,
        width: int,
        height: int,
        fps: float,
    ) -> None:
        self.gateway_path = gateway_path
        self.width = width
        self.height = height
        self.fps = max(1.0, fps)
        self.process: subprocess.Popen[bytes] | None = None

    def _publish_url(self) -> str:
        base = os.getenv(
            "MEDIAMTX_RTSP_BASE_URL",
            "rtsp://mediamtx:8554",
        ).rstrip("/")
        username = os.getenv(
            "LIVE_STREAM_PUBLISH_USERNAME",
            "",
        )
        password = os.getenv(
            "LIVE_STREAM_PUBLISH_PASSWORD",
            "",
        )

        if username:
            prefix = "rtsp://"
            if not base.startswith(prefix):
                raise ValueError(
                    "MEDIAMTX_RTSP_BASE_URL must start with rtsp://"
                )
            authority = base[len(prefix):]
            auth = quote(username, safe="")
            if password:
                auth += ":" + quote(password, safe="")
            base = f"{prefix}{auth}@{authority}"

        return f"{base}/{self.gateway_path}"

    def start(self) -> None:
        if self.process is not None:
            raise RuntimeError("Publisher is already running.")

        publish_url = self._publish_url()
        frame_rate = f"{self.fps:.3f}"

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            os.getenv("FFMPEG_LOG_LEVEL", "warning"),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-video_size",
            f"{self.width}x{self.height}",
            "-framerate",
            frame_rate,
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            os.getenv("V380_H264_PRESET", "ultrafast"),
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-bf",
            "0",
            "-g",
            str(max(12, round(self.fps * 2))),
            "-keyint_min",
            str(max(12, round(self.fps * 2))),
            "-sc_threshold",
            "0",
            "-rtsp_transport",
            "tcp",
            "-f",
            "rtsp",
            publish_url,
        ]

        print(
            f"[PUBLISH:{self.gateway_path}] "
            f"Starting H.264 RTSP publisher "
            f"({self.width}x{self.height} @ {self.fps:.1f} fps).",
            flush=True,
        )

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
        )

    def write_bgr(self, frame_bytes: bytes) -> None:
        process = self.process
        if process is None or process.stdin is None:
            raise RuntimeError("Publisher has not been started.")

        if process.poll() is not None:
            raise RuntimeError(
                f"ffmpeg publisher exited with code {process.returncode}."
            )

        try:
            process.stdin.write(frame_bytes)
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError(
                "MediaMTX publisher pipe was closed."
            ) from exc

    def close(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return

        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass

        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
