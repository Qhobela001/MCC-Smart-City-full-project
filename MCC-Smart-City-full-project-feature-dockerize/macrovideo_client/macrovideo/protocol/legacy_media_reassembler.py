from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final, Iterator


TRANSPORT_HEADER_SIZE: Final[int] = 12
MAX_FRAGMENT_PAYLOAD: Final[int] = 500


@dataclass(frozen=True)
class LegacyMediaFragment:
    """
    One V2 transport fragment.

    Recovered from HSLiveDataV2Transmitter::getDataFromDevice():

        uint16 at +3 -> total fragment count
        uint16 at +5 -> fragment index
        uint16 at +7 -> fragment payload length

    The native code rejects payload lengths > 500 and copies each
    fragment to frame_buffer + fragment_index * 500.
    """

    raw_header: bytes
    fragment_count: int
    fragment_index: int
    payload_length: int
    payload: bytes

    @property
    def is_last_fragment(self) -> bool:
        return self.fragment_index == self.fragment_count - 1


@dataclass(frozen=True)
class LegacyMediaFrame:
    sequence: int
    fragment_count: int
    payload: bytes

    @property
    def size(self) -> int:
        return len(self.payload)


@dataclass(frozen=True)
class LegacyMediaParseSummary:
    fragment_count: int
    frame_count: int
    consumed_bytes: int
    trailing_bytes: int
    frames: tuple[LegacyMediaFrame, ...]


def parse_fragment_header(
    raw_header: bytes,
) -> tuple[int, int, int]:
    if len(raw_header) != TRANSPORT_HEADER_SIZE:
        raise ValueError(
            "V380 V2 media transport header must be "
            f"{TRANSPORT_HEADER_SIZE} bytes."
        )

    fragment_count = struct.unpack_from(
        "<H",
        raw_header,
        3,
    )[0]

    fragment_index = struct.unpack_from(
        "<H",
        raw_header,
        5,
    )[0]

    payload_length = struct.unpack_from(
        "<H",
        raw_header,
        7,
    )[0]

    if fragment_count <= 0:
        raise ValueError(
            "Fragment count must be positive."
        )

    if fragment_index >= fragment_count:
        raise ValueError(
            "Fragment index is outside the frame: "
            f"index={fragment_index}, "
            f"count={fragment_count}."
        )

    if payload_length > MAX_FRAGMENT_PAYLOAD:
        raise ValueError(
            "Fragment payload exceeds native limit: "
            f"{payload_length} > {MAX_FRAGMENT_PAYLOAD}."
        )

    return (
        fragment_count,
        fragment_index,
        payload_length,
    )


def iter_fragments(
    data: bytes,
) -> Iterator[LegacyMediaFragment]:
    offset = 0

    while (
        offset + TRANSPORT_HEADER_SIZE
        <= len(data)
    ):
        raw_header = data[
            offset:
            offset + TRANSPORT_HEADER_SIZE
        ]

        try:
            (
                fragment_count,
                fragment_index,
                payload_length,
            ) = parse_fragment_header(
                raw_header
            )
        except ValueError:
            # The live capture begins at a true packet boundary in the
            # current collector. If a future capture does not, stop
            # rather than silently guessing a resync point.
            break

        payload_start = (
            offset + TRANSPORT_HEADER_SIZE
        )
        payload_end = (
            payload_start + payload_length
        )

        if payload_end > len(data):
            break

        payload = data[
            payload_start:
            payload_end
        ]

        yield LegacyMediaFragment(
            raw_header=raw_header,
            fragment_count=fragment_count,
            fragment_index=fragment_index,
            payload_length=payload_length,
            payload=payload,
        )

        offset = payload_end


def reassemble_frames(
    data: bytes,
) -> LegacyMediaParseSummary:
    frames: list[LegacyMediaFrame] = []

    current_count: int | None = None
    fragments: dict[int, bytes] = {}

    parsed_fragments = 0
    consumed = 0

    for fragment in iter_fragments(data):
        parsed_fragments += 1
        consumed += (
            TRANSPORT_HEADER_SIZE
            + fragment.payload_length
        )

        if fragment.fragment_index == 0:
            current_count = (
                fragment.fragment_count
            )
            fragments = {}

        if current_count is None:
            continue

        if (
            fragment.fragment_count
            != current_count
        ):
            current_count = (
                fragment.fragment_count
            )
            fragments = {}

        fragments[
            fragment.fragment_index
        ] = fragment.payload

        if fragment.is_last_fragment:
            expected = range(current_count)

            if all(
                index in fragments
                for index in expected
            ):
                frame_payload = b"".join(
                    fragments[index]
                    for index in expected
                )

                frames.append(
                    LegacyMediaFrame(
                        sequence=len(frames),
                        fragment_count=(
                            current_count
                        ),
                        payload=frame_payload,
                    )
                )

            current_count = None
            fragments = {}

    return LegacyMediaParseSummary(
        fragment_count=parsed_fragments,
        frame_count=len(frames),
        consumed_bytes=consumed,
        trailing_bytes=max(
            0,
            len(data) - consumed,
        ),
        frames=tuple(frames),
    )


def write_frames(
    frames: tuple[LegacyMediaFrame, ...],
    directory: str | Path,
) -> tuple[Path, ...]:
    output_directory = Path(directory)
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    written: list[Path] = []

    for frame in frames:
        path = (
            output_directory
            / f"frame_{frame.sequence:06d}.bin"
        )

        path.write_bytes(
            frame.payload
        )
        written.append(path)

    return tuple(written)


def inspect_frame_prefix(
    frame: LegacyMediaFrame,
    *,
    prefix_size: int = 64,
) -> str:
    return frame.payload[
        :prefix_size
    ].hex()
