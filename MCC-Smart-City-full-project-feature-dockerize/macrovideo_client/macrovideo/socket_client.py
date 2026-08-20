from __future__ import annotations

import socket
from dataclasses import replace

from .config import CameraConfig
from .constants import COMMON_HEADER_SIZE
from .packet import CommonPacket, unpack_common_header


class CameraSocket:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self.socket is not None

    def connect(self) -> None:
        if self.socket is not None:
            raise RuntimeError("Socket is already connected.")

        connection = socket.create_connection(
            (self.config.ip, self.config.port),
            timeout=self.config.timeout,
        )

        connection.settimeout(self.config.timeout)
        self.socket = connection

    def send_all(self, data: bytes) -> None:
        if self.socket is None:
            raise RuntimeError("Socket is not connected.")

        self.socket.sendall(data)

    def receive_exact(self, size: int) -> bytes:
        if self.socket is None:
            raise RuntimeError("Socket is not connected.")

        if size < 0:
            raise ValueError("size cannot be negative")

        received = bytearray()

        while len(received) < size:
            chunk = self.socket.recv(size - len(received))

            if not chunk:
                raise ConnectionError(
                    "Camera closed the connection after "
                    f"{len(received)} of {size} bytes."
                )

            received.extend(chunk)

        return bytes(received)

    def receive_common_packet(self) -> CommonPacket:
        header = self.receive_exact(COMMON_HEADER_SIZE)
        packet, payload_size = unpack_common_header(header)

        payload = self.receive_exact(payload_size)

        return replace(
            packet,
            payload=payload,
        )

    def close(self) -> None:
        if self.socket is None:
            return

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.socket.close()
            self.socket = None

    def __enter__(self) -> "CameraSocket":
        self.connect()
        return self

    def __exit__(
        self,
        exception_type: object,
        exception: object,
        traceback: object,
    ) -> None:
        self.close()