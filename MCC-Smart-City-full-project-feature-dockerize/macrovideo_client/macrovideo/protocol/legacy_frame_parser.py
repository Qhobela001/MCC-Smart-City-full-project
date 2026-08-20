
from __future__ import annotations
import struct
from dataclasses import dataclass
from pathlib import Path
from macrovideo.crypto.legacy_media_crypto import decrypt_media_payload_pre_2k

FRAME_HEADER_SIZE = 16
SPECIAL_MEDIA_TYPES = {0x15, 0x16, 0x18, 0x19, 0x1A}
CONTROL_MEDIA_TYPES = {0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60}

@dataclass(frozen=True)
class LegacyDecodedFrame:
    sequence: int
    frame_id: int
    frame_type: int
    frame_rate: int
    timestamp: int
    raw_payload: bytes
    decrypted_payload: bytes

    @property
    def is_control(self) -> bool:
        return self.frame_type in CONTROL_MEDIA_TYPES

@dataclass(frozen=True)
class CodecDetection:
    codec: str | None
    annexb_start_codes: int
    h264_nal_types: tuple[int, ...]
    h265_nal_types: tuple[int, ...]

def parse_legacy_frame(frame_blob: bytes, *, sequence: int, login_handle: int) -> LegacyDecodedFrame:
    if len(frame_blob) < FRAME_HEADER_SIZE:
        raise ValueError(f"Frame too small: {len(frame_blob)} bytes.")
    frame_id = struct.unpack_from("<I", frame_blob, 0)[0]
    frame_type = struct.unpack_from("<H", frame_blob, 4)[0]
    frame_rate = struct.unpack_from("<H", frame_blob, 6)[0]
    timestamp = struct.unpack_from("<Q", frame_blob, 8)[0]
    raw_payload = frame_blob[16:]
    decrypted = decrypt_media_payload_pre_2k(
        raw_payload,
        login_handle=login_handle,
        special_media=frame_type in SPECIAL_MEDIA_TYPES,
    )
    return LegacyDecodedFrame(
        sequence=sequence,
        frame_id=frame_id,
        frame_type=frame_type,
        frame_rate=frame_rate,
        timestamp=timestamp,
        raw_payload=raw_payload,
        decrypted_payload=decrypted,
    )

def _iter_annexb_nals(data: bytes):
    starts = []
    i = 0
    while i <= len(data) - 3:
        if data[i:i+4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        elif data[i:i+3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        else:
            i += 1

    for idx, (start, prefix) in enumerate(starts):
        nal_start = start + prefix
        nal_end = starts[idx+1][0] if idx + 1 < len(starts) else len(data)
        if nal_end > nal_start:
            yield data[nal_start:nal_end]

def detect_annexb_codec(payloads: list[bytes]) -> CodecDetection:
    h264, h265 = [], []
    count = 0
    for payload in payloads:
        for nal in _iter_annexb_nals(payload):
            if not nal:
                continue
            count += 1
            h264.append(nal[0] & 0x1F)
            if len(nal) >= 2:
                h265.append((nal[0] >> 1) & 0x3F)

    h264_score = sum(x in {1,5,6,7,8,9} for x in h264)
    h265_score = sum(x in {1,19,20,32,33,34,35,39,40} for x in h265)

    codec = None
    if h264_score > h265_score:
        codec = "h264"
    elif h265_score > h264_score:
        codec = "h265"

    return CodecDetection(codec, count, tuple(h264[:64]), tuple(h265[:64]))

def write_elementary_stream(frames: list[LegacyDecodedFrame], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        for frame in frames:
            if not frame.is_control and frame.decrypted_payload:
                fh.write(frame.decrypted_payload)
    return path
