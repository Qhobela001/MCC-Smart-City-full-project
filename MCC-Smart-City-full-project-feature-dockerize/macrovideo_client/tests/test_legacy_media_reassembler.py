from __future__ import annotations

import os
import sys
from pathlib import Path

from macrovideo.protocol.legacy_media_reassembler import (
    reassemble_frames,
    write_frames,
)


RAW_PATH = Path(
    os.getenv(
        "V380_LIVE_RAW_OUTPUT",
        "v380_live_stream.raw",
    )
)

FRAME_DIRECTORY = Path(
    os.getenv(
        "V380_FRAME_OUTPUT_DIR",
        "v380_frames",
    )
)


def main() -> int:
    print("=" * 72)
    print(
        "V380 LEGACY V2 MEDIA "
        "FRAGMENT REASSEMBLY TEST"
    )
    print("=" * 72)

    if not RAW_PATH.exists():
        print(
            "[!] Raw stream file does not exist: "
            f"{RAW_PATH.resolve()}"
        )
        return 1

    data = RAW_PATH.read_bytes()

    print(
        f"Raw stream: {RAW_PATH.resolve()}"
    )
    print(
        f"Raw size: {len(data)} bytes"
    )

    result = reassemble_frames(data)

    print(
        f"Transport fragments parsed: "
        f"{result.fragment_count}"
    )
    print(
        f"Complete frames reassembled: "
        f"{result.frame_count}"
    )
    print(
        f"Consumed bytes: "
        f"{result.consumed_bytes}"
    )
    print(
        f"Trailing bytes: "
        f"{result.trailing_bytes}"
    )

    if not result.frames:
        print(
            "[!] No complete frames were "
            "reassembled."
        )
        return 2

    paths = write_frames(
        result.frames,
        FRAME_DIRECTORY,
    )

    print(
        f"\n[+] Wrote {len(paths)} "
        f"reassembled frames to "
        f"{FRAME_DIRECTORY.resolve()}"
    )

    preview_count = min(
        10,
        len(result.frames),
    )

    print(
        "\nFirst reassembled frames:"
    )

    for frame in result.frames[
        :preview_count
    ]:
        print("-" * 72)
        print(
            f"Frame: {frame.sequence}"
        )
        print(
            f"Fragments: "
            f"{frame.fragment_count}"
        )
        print(
            f"Frame size: "
            f"{frame.size} bytes"
        )
        print(
            "First 64 bytes: "
            f"{frame.payload[:64].hex()}"
        )

    print(
        "\n[+] Transport-layer "
        "reassembly succeeded."
    )
    print(
        "[+] The next layer is "
        "parseFrameDataV20(), which "
        "interprets each reassembled "
        "frame as video/audio metadata "
        "plus encoded payload."
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
