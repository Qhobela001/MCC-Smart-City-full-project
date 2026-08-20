from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final


PACKET_SIZE: Final[int] = 256
START_RESPONSE_SIZE: Final[int] = 32
STOP_PACKET_SIZE: Final[int] = 16

CMD_START: Final[int] = 301
CMD_CONTINUE: Final[int] = 303
CMD_START_RESPONSE: Final[int] = 401
CMD_STOP: Final[int] = 1008
RESULT_OK: Final[int] = 1001


@dataclass(frozen=True)
class LegacyLiveSession:
    device_id: int
    login_handle: int
    token_session: int
    protocol_version: int

    def __post_init__(self) -> None:
        if self.device_id <= 0:
            raise ValueError("Device ID must be positive.")
        if self.login_handle <= 0:
            raise ValueError("Login handle must be positive.")
        if self.token_session < 0:
            raise ValueError("Token session cannot be negative.")
        if self.protocol_version < 0:
            raise ValueError("Protocol version cannot be negative.")


@dataclass(frozen=True)
class LiveStartResponse:
    command: int
    result: int
    device_version: int
    width: int
    height: int
    max_packet_size: int
    audio_frequency_flag: int
    audio_bits: int
    channel: int
    raw: bytes


@dataclass(frozen=True)
class LiveStreamProbeResult:
    start_response: LiveStartResponse
    bytes_received: int
    output_path: Path
    first_media_bytes: bytes


def build_live_start_request(
    *,
    session: LegacyLiveSession,
) -> bytes:
    """
    Exact command-301 layout recovered from
    HSLiveDataV2Transmitter::getDataFromDevice() and verified against
    the successful official-client packet capture.

    Important corrections:
      offset 0x16 is integer 1, not 0x1000
      offset 0x1A is integer 0 for this stream
      offset 0x0E is the current LAN login handle
    """

    packet = bytearray(PACKET_SIZE)

    communication_version = (
        0x15
        if session.protocol_version == 0x20
        else 0x14
    )

    struct.pack_into("<I", packet, 0x00, CMD_START)
    struct.pack_into("<I", packet, 0x04, session.device_id)
    struct.pack_into("<I", packet, 0x08, 0)
    struct.pack_into("<H", packet, 0x0C, communication_version)
    struct.pack_into("<I", packet, 0x0E, session.login_handle)

    # Native: *(undefined4 *)(param_2 + 0x16) = uVar20.
    # The successful captured request proves this value is 1.
    struct.pack_into("<I", packet, 0x16, 1)

    # Native: *(undefined4 *)(param_2 + 0x1A) =
    #         *(undefined4 *)(this + 0x2c).
    # The successful captured request proves this value is 0.
    struct.pack_into("<I", packet, 0x1A, 0)

    packet[0x1E] = 1
    packet[0x1F] = 1
    packet[0x20] = 1

    return bytes(packet)


def build_live_continue_request() -> bytes:
    packet = bytearray(PACKET_SIZE)
    struct.pack_into("<I", packet, 0x00, CMD_CONTINUE)
    packet[0x04:0x08] = b"\x01\x30\x00\x00"
    return bytes(packet)


def build_live_stop_request() -> bytes:
    packet = bytearray(STOP_PACKET_SIZE)
    struct.pack_into("<I", packet, 0x00, CMD_STOP)
    return bytes(packet)


def parse_live_start_response(raw: bytes) -> LiveStartResponse:
    if len(raw) != START_RESPONSE_SIZE:
        raise ValueError(
            f"Expected {START_RESPONSE_SIZE} response bytes, "
            f"received {len(raw)}."
        )

    return LiveStartResponse(
        command=struct.unpack_from("<I", raw, 0x00)[0],
        result=struct.unpack_from("<i", raw, 0x04)[0],
        device_version=struct.unpack_from("<H", raw, 0x08)[0],
        width=struct.unpack_from("<I", raw, 0x0A)[0],
        height=struct.unpack_from("<I", raw, 0x0E)[0],
        max_packet_size=struct.unpack_from("<I", raw, 0x12)[0],
        audio_frequency_flag=raw[0x16],
        audio_bits=raw[0x17],
        channel=raw[0x18],
        raw=raw,
    )


def probe_legacy_live_stream(
    *,
    host: str,
    port: int,
    session: LegacyLiveSession,
    output_path: str | Path,
    capture_seconds: float = 8.0,
    connect_timeout: float = 5.0,
    read_timeout: float = 2.0,
) -> LiveStreamProbeResult:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    request = build_live_start_request(session=session)
    continuation = build_live_continue_request()
    stop_packet = build_live_stop_request()

    print(f"[LIVE] Connecting to {host}:{port}")
    print(f"[LIVE] Current login handle: {session.login_handle}")
    print(
        "[LIVE] Handle bytes at offset 0x0E: "
        f"{request[0x0E:0x12].hex()}"
    )
    print(
        "[LIVE] Offset 0x16 value: "
        f"{struct.unpack_from('<I', request, 0x16)[0]}"
    )
    print(
        "[LIVE] Offset 0x1A value: "
        f"{struct.unpack_from('<I', request, 0x1A)[0]}"
    )
    print(
        "[LIVE] Start request first 40 bytes: "
        f"{request[:40].hex()}"
    )

    received = 0
    first_media = bytearray()

    try:
        with socket.create_connection(
            (host, port),
            timeout=connect_timeout,
        ) as sock:
            sock.settimeout(read_timeout)

            print("[LIVE] TCP connection established.")
            sock.sendall(request)
            print("[LIVE] Corrected 256-byte command 301 sent.")

            raw_response = _recv_exact(sock, START_RESPONSE_SIZE)
            response = parse_live_start_response(raw_response)

            print(f"[LIVE] Start response: {raw_response.hex()}")
            print(f"[LIVE] Response command: {response.command}")
            print(f"[LIVE] Response result: {response.result}")

            if response.command != CMD_START_RESPONSE:
                raise ValueError(
                    f"Unexpected response command {response.command}; "
                    f"expected {CMD_START_RESPONSE}."
                )

            if response.result != RESULT_OK:
                raise PermissionError(
                    "Camera rejected command 301 with signed result "
                    f"{response.result}."
                )

            print("[+] Command 301 accepted.")
            print(
                "[LIVE] Stream properties: "
                f"device_version={response.device_version}, "
                f"width={response.width}, "
                f"height={response.height}, "
                f"max_packet_size={response.max_packet_size}, "
                f"audio_flag={response.audio_frequency_flag}, "
                f"audio_bits={response.audio_bits}, "
                f"channel={response.channel}"
            )

            sock.sendall(continuation)
            print("[LIVE] 256-byte command 303 sent.")
            print(
                f"[LIVE] Capturing media for "
                f"{capture_seconds:.1f} seconds..."
            )

            deadline = time.monotonic() + capture_seconds

            with destination.open("wb") as output:
                while time.monotonic() < deadline:
                    try:
                        chunk = sock.recv(65536)
                    except socket.timeout:
                        continue

                    if not chunk:
                        print("[LIVE] Camera closed the media socket.")
                        break

                    output.write(chunk)
                    received += len(chunk)

                    if len(first_media) < 256:
                        remaining = 256 - len(first_media)
                        first_media.extend(chunk[:remaining])

            try:
                sock.sendall(stop_packet)
                print("[LIVE] 16-byte command 1008 sent.")
            except OSError:
                pass

    except socket.timeout as error:
        raise TimeoutError(
            "Timed out during the live-stream exchange."
        ) from error
    except (PermissionError, ValueError):
        raise
    except OSError as error:
        raise ConnectionError(
            f"Live-stream network failure for {host}:{port}: {error}"
        ) from error

    return LiveStreamProbeResult(
        start_response=response,
        bytes_received=received,
        output_path=destination,
        first_media_bytes=bytes(first_media),
    )


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            raise ConnectionError(
                "Camera closed the connection after "
                f"{len(data)} of {size} expected bytes."
            )

        data.extend(chunk)

    return bytes(data)
