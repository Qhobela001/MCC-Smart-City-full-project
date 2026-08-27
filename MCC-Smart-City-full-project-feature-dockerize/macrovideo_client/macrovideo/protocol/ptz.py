from __future__ import annotations

from enum import StrEnum
from typing import Final


class PTZDirection(StrEnum):
    up = "up"
    down = "down"
    left = "left"
    right = "right"


class PTZHead(StrEnum):
    main = "main"
    right = "right"
    left = "left"


_HEAD_CHANNELS: Final[dict[PTZHead, int]] = {
    PTZHead.main: 0,
    PTZHead.right: 1,
    PTZHead.left: 2,
}


# Packet reconstructed from the official Windows V380 client's
# HS_DevicePreview.dll (PreviewHelper::PTZTurn). Values are little-endian
# 16-bit words. An unused axis must remain zero.
_BASE_PACKET: Final[bytes] = bytes.fromhex(
    "aa000000e803e8030000000000000100"
)
_HORIZONTAL_COMMANDS: Final[dict[PTZDirection, int]] = {
    PTZDirection.up: 0x03EB,
    PTZDirection.down: 0x03EC,
}
_VERTICAL_COMMANDS: Final[dict[PTZDirection, int]] = {
    PTZDirection.left: 0x03E9,
    PTZDirection.right: 0x03EA,
}


def build_ptz_packet(
    direction: PTZDirection | str,
    head: PTZHead | str = PTZHead.main,
) -> bytes:
    """Build one authenticated-live-socket V380 movement nudge."""
    try:
        selected = PTZDirection(direction)
    except ValueError as exc:
        raise ValueError(f"Unsupported PTZ direction: {direction}.") from exc

    try:
        selected_head = PTZHead(head)
    except ValueError as exc:
        raise ValueError(f"Unsupported PTZ head: {head}.") from exc
    packet = bytearray(_BASE_PACKET)
    channel = _HEAD_CHANNELS[selected_head]
    packet[12:14] = channel.to_bytes(2, "little")
    if selected in _HORIZONTAL_COMMANDS:
        packet[10:12] = _HORIZONTAL_COMMANDS[selected].to_bytes(2, "little")
    else:
        packet[8:10] = _VERTICAL_COMMANDS[selected].to_bytes(2, "little")
    return bytes(packet)
