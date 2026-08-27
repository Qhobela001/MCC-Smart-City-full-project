from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Final, Iterator

from macrovideo.protocol.legacy_frame_parser import (
    LegacyDecodedFrame,
    parse_legacy_frame,
)
from macrovideo.protocol.legacy_live_stream import (
    CMD_START_RESPONSE,
    RESULT_OK,
    LegacyLiveSession,
    LiveStartResponse,
    build_live_continue_request,
    build_live_start_request,
    build_live_stop_request,
    parse_live_start_response,
)
from macrovideo.protocol.legacy_media_reassembler import (
    TRANSPORT_HEADER_SIZE,
    parse_fragment_header,
)
from macrovideo.protocol.ptz import PTZDirection, PTZHead, build_ptz_packet


VIDEO_FRAME_TYPES: Final[set[int]] = {
    0x28,
    0x29,
}


@dataclass(frozen=True)
class LegacyLiveClientStats:
    transport_fragments: int
    complete_frames: int
    video_frames: int
    non_video_frames: int
    media_bytes: int


class LegacyFrameAssembler:
    """
    Incremental V380 V2 frame reassembler.

    The important reliability property is that a temporary TCP timeout
    does not reset this object. If a fragment header/payload arrives in
    several TCP reads, _recv_exact() preserves those bytes until the
    requested length is complete.
    """

    def __init__(self) -> None:
        self._expected_count: int | None = None
        self._fragments: dict[int, bytes] = {}

    def reset(self) -> None:
        self._expected_count = None
        self._fragments = {}

    def push(
        self,
        *,
        fragment_count: int,
        fragment_index: int,
        payload: bytes,
    ) -> bytes | None:
        if fragment_index == 0:
            self._expected_count = fragment_count
            self._fragments = {}

        if self._expected_count is None:
            return None

        if fragment_count != self._expected_count:
            self._expected_count = fragment_count
            self._fragments = {}

        self._fragments[fragment_index] = payload

        if fragment_index != fragment_count - 1:
            return None

        if not all(
            index in self._fragments
            for index in range(fragment_count)
        ):
            self.reset()
            return None

        frame = b"".join(
            self._fragments[index]
            for index in range(fragment_count)
        )

        self.reset()
        return frame


class LegacyV2LiveClient:
    """
    Long-running direct-LAN V380 V2 media client.

    Proven pipeline:
        command 301
        -> response 401/result 1001
        -> command 303
        -> 12-byte V2 transport records
        -> fragment reassembly
        -> 16-byte media-frame header
        -> AES-128-ECB media decrypt
        -> HEVC payload

    Temporary socket timeouts are tolerated without losing partially
    received packet bytes. A TimeoutError is raised only after the
    connection has made no receive progress for idle_timeout seconds.
    The caller can then perform a full fresh LAN login/reconnect.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        session: LegacyLiveSession,
        connect_timeout: float = 5.0,
        socket_timeout: float = 2.0,
        idle_timeout: float = 20.0,
    ) -> None:
        self.host = host.strip()
        self.port = port
        self.session = session
        self.connect_timeout = connect_timeout
        self.socket_timeout = socket_timeout
        self.idle_timeout = idle_timeout

        self._socket: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._start_response: LiveStartResponse | None = None
        self._assembler = LegacyFrameAssembler()
        self._sequence = 0

        self._transport_fragments = 0
        self._complete_frames = 0
        self._video_frames = 0
        self._non_video_frames = 0
        self._media_bytes = 0

        if not self.host:
            raise ValueError("Camera host cannot be empty.")

        if not 1 <= self.port <= 65535:
            raise ValueError(
                "Camera port must be between 1 and 65535."
            )

        if self.connect_timeout <= 0:
            raise ValueError(
                "connect_timeout must be positive."
            )

        if self.socket_timeout <= 0:
            raise ValueError(
                "socket_timeout must be positive."
            )

        if self.idle_timeout <= 0:
            raise ValueError(
                "idle_timeout must be positive."
            )

    @property
    def start_response(self) -> LiveStartResponse | None:
        return self._start_response

    @property
    def stats(self) -> LegacyLiveClientStats:
        return LegacyLiveClientStats(
            transport_fragments=self._transport_fragments,
            complete_frames=self._complete_frames,
            video_frames=self._video_frames,
            non_video_frames=self._non_video_frames,
            media_bytes=self._media_bytes,
        )

    def connect(self) -> LiveStartResponse:
        if self._socket is not None:
            raise RuntimeError(
                "Live client is already connected."
            )

        request = build_live_start_request(
            session=self.session,
        )

        sock = socket.create_connection(
            (self.host, self.port),
            timeout=self.connect_timeout,
        )
        sock.settimeout(self.socket_timeout)

        try:
            print(
                f"[LIVE] Connected to "
                f"{self.host}:{self.port}"
            )
            print(
                f"[LIVE] Using fresh login handle: "
                f"{self.session.login_handle}"
            )

            sock.sendall(request)
            print("[LIVE] Command 301 sent.")

            raw_response = _recv_exact(
                sock,
                32,
                idle_timeout=self.idle_timeout,
            )

            response = parse_live_start_response(
                raw_response
            )

            print(
                "[LIVE] Command 401 response: "
                f"result={response.result}, "
                f"device_version={response.device_version}, "
                f"width={response.width}, "
                f"height={response.height}, "
                f"channel={response.channel}"
            )

            if response.command != CMD_START_RESPONSE:
                raise ValueError(
                    "Unexpected live-start response "
                    f"command {response.command}; "
                    f"expected {CMD_START_RESPONSE}."
                )

            if response.result != RESULT_OK:
                raise PermissionError(
                    "Camera rejected command 301 "
                    f"with signed result {response.result}."
                )

            sock.sendall(
                build_live_continue_request()
            )
            print(
                "[LIVE] Command 303 sent; "
                "live media is active."
            )

            self._socket = sock
            self._start_response = response
            return response

        except Exception:
            sock.close()
            raise

    def iter_decoded_frames(
        self,
    ) -> Iterator[LegacyDecodedFrame]:
        sock = self._require_socket()

        while True:
            header = _recv_exact(
                sock,
                TRANSPORT_HEADER_SIZE,
                idle_timeout=self.idle_timeout,
            )

            (
                fragment_count,
                fragment_index,
                payload_length,
            ) = parse_fragment_header(
                header
            )

            payload = _recv_exact(
                sock,
                payload_length,
                idle_timeout=self.idle_timeout,
            )

            self._transport_fragments += 1
            self._media_bytes += (
                TRANSPORT_HEADER_SIZE
                + payload_length
            )

            frame_blob = self._assembler.push(
                fragment_count=fragment_count,
                fragment_index=fragment_index,
                payload=payload,
            )

            if frame_blob is None:
                continue

            frame = parse_legacy_frame(
                frame_blob,
                sequence=self._sequence,
                login_handle=(
                    self.session.login_handle
                ),
            )

            self._sequence += 1
            self._complete_frames += 1

            if frame.frame_type in VIDEO_FRAME_TYPES:
                self._video_frames += 1
            else:
                self._non_video_frames += 1

            yield frame

    def iter_hevc_payloads(
        self,
    ) -> Iterator[
        tuple[LegacyDecodedFrame, bytes]
    ]:
        for frame in self.iter_decoded_frames():
            if (
                frame.frame_type
                not in VIDEO_FRAME_TYPES
            ):
                continue

            payload = frame.decrypted_payload

            if not payload:
                continue

            if not _contains_annexb_start_code(
                payload
            ):
                continue

            yield frame, payload

    def close(self) -> None:
        sock = self._socket
        self._socket = None

        if sock is None:
            return

        with self._send_lock:
            try:
                sock.sendall(build_live_stop_request())
                print("[LIVE] Command 1008 sent.")
            except OSError:
                pass

        try:
            sock.shutdown(
                socket.SHUT_RDWR
            )
        except OSError:
            pass

        sock.close()
        self._assembler.reset()

    def send_ptz(
        self,
        direction: PTZDirection | str,
        head: PTZHead | str = PTZHead.main,
    ) -> None:
        """Send one PTZ nudge without disturbing media reception."""
        packet = build_ptz_packet(direction, head)
        with self._send_lock:
            sock = self._require_socket()
            sock.sendall(packet)

    def _require_socket(
        self,
    ) -> socket.socket:
        if self._socket is None:
            raise RuntimeError(
                "Live client is not connected."
            )

        return self._socket


def _recv_exact(
    sock: socket.socket,
    size: int,
    *,
    idle_timeout: float,
) -> bytes:
    """
    Receive exactly size bytes while tolerating transient socket timeouts.

    Crucially, the partially accumulated buffer is NOT discarded when
    socket.recv() times out. This prevents TCP packet alignment loss.

    A TimeoutError is raised only after no receive progress has occurred
    for idle_timeout seconds.
    """

    if size < 0:
        raise ValueError(
            "Requested receive size cannot be negative."
        )

    if size == 0:
        return b""

    data = bytearray()
    last_progress = time.monotonic()

    while len(data) < size:
        try:
            chunk = sock.recv(
                size - len(data)
            )
        except socket.timeout:
            idle_for = (
                time.monotonic()
                - last_progress
            )

            if idle_for >= idle_timeout:
                raise TimeoutError(
                    "Camera live-media socket was "
                    f"idle for {idle_for:.1f}s while "
                    f"waiting for {size} bytes "
                    f"({len(data)} received)."
                )

            continue

        if not chunk:
            raise ConnectionError(
                "Camera closed the live-media "
                "connection after "
                f"{len(data)} of {size} "
                "expected bytes."
            )

        data.extend(chunk)
        last_progress = time.monotonic()

    return bytes(data)


def _contains_annexb_start_code(
    payload: bytes,
) -> bool:
    return (
        b"\x00\x00\x00\x01" in payload
        or b"\x00\x00\x01" in payload
    )
