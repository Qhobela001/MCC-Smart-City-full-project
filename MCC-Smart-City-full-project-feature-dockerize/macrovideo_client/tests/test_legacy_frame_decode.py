
from __future__ import annotations
import json, os, sys
from collections import Counter
from pathlib import Path

from macrovideo.crypto.legacy_media_crypto import derive_legacy_media_key
from macrovideo.protocol.legacy_frame_parser import (
    detect_annexb_codec,
    parse_legacy_frame,
    write_elementary_stream,
)

FRAME_DIRECTORY = Path(os.getenv("V380_FRAME_OUTPUT_DIR", "v380_frames"))
LOGIN_HANDLE = int(os.getenv("V380_LIVE_LOGIN_HANDLE", "55078"))
OUTPUT_DIRECTORY = Path(os.getenv("V380_DECODE_OUTPUT_DIR", "v380_decoded"))

def main() -> int:
    print("=" * 72)
    print("V380 LEGACY V2 FRAME DECRYPT + CODEC DETECTION TEST")
    print("=" * 72)

    files = sorted(FRAME_DIRECTORY.glob("frame_*.bin"))
    if not files:
        print(f"[!] No frames found in {FRAME_DIRECTORY.resolve()}")
        return 1

    key = derive_legacy_media_key(LOGIN_HANDLE)
    print(f"Login handle: {LOGIN_HANDLE}")
    print(f"Derived AES key: {key.key.hex()}")
    print(f"Frames found: {len(files)}")

    decoded = []
    for i, path in enumerate(files):
        decoded.append(
            parse_legacy_frame(
                path.read_bytes(),
                sequence=i,
                login_handle=LOGIN_HANDLE,
            )
        )

    counts = Counter(f.frame_type for f in decoded)
    print("\nFrame types:")
    for ft, count in sorted(counts.items()):
        print(f"  0x{ft:02x} ({ft}): {count}")

    payloads = [f.decrypted_payload for f in decoded if not f.is_control and f.decrypted_payload]
    detection = detect_annexb_codec(payloads)

    print("\nAnnex-B scan:")
    print(f"Start codes found: {detection.annexb_start_codes}")
    print(f"Detected codec: {detection.codec or '<unknown>'}")
    print(f"Sample H.264 NAL types: {detection.h264_nal_types}")
    print(f"Sample H.265 NAL types: {detection.h265_nal_types}")

    print("\nFirst decoded frames:")
    for f in decoded[:12]:
        print("-" * 72)
        print(f"Sequence: {f.sequence}")
        print(f"Frame ID: {f.frame_id}")
        print(f"Type: 0x{f.frame_type:02x}")
        print(f"Frame rate: {f.frame_rate}")
        print(f"Timestamp: {f.timestamp}")
        print(f"Payload size: {len(f.decrypted_payload)}")
        print(f"First 64 bytes: {f.decrypted_payload[:64].hex()}")

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    out = None
    if detection.codec:
        suffix = ".h264" if detection.codec == "h264" else ".h265"
        out = write_elementary_stream(decoded, OUTPUT_DIRECTORY / f"camera_live{suffix}")
        print(f"\n[+] Elementary stream written to: {out.resolve()}")
    else:
        print("\n[!] No Annex-B codec detected yet.")
        print("[!] The decrypted payload may contain one additional media wrapper/header.")

    summary = {
        "login_handle": LOGIN_HANDLE,
        "aes_key_hex": key.key.hex(),
        "frames_found": len(files),
        "frames_decoded": len(decoded),
        "frame_type_counts": {f"0x{k:02x}": v for k, v in sorted(counts.items())},
        "annexb_start_codes": detection.annexb_start_codes,
        "detected_codec": detection.codec,
        "h264_nal_types": list(detection.h264_nal_types),
        "h265_nal_types": list(detection.h265_nal_types),
        "output_stream": str(out) if out else None,
    }
    (OUTPUT_DIRECTORY / "frame_decode_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"[+] Summary written to: {(OUTPUT_DIRECTORY / 'frame_decode_summary.json').resolve()}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
