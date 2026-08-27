from __future__ import annotations

from macrovideo.protocol.ptz import build_ptz_packet


def test_ptz_packets_match_official_client_and_camera_orientation() -> None:
    assert build_ptz_packet("left").hex() == (
        "aa000000e803e803e903000000000100"
    )
    assert build_ptz_packet("right").hex() == (
        "aa000000e803e803ea03000000000100"
    )
    assert build_ptz_packet("up").hex() == (
        "aa000000e803e8030000eb0300000100"
    )
    assert build_ptz_packet("down").hex() == (
        "aa000000e803e8030000ec0300000100"
    )
    assert build_ptz_packet("up", head="left").hex() == (
        "aa000000e803e8030000eb0302000100"
    )
    assert build_ptz_packet("up", head="right").hex() == (
        "aa000000e803e8030000eb0301000100"
    )


def test_ptz_packet_rejects_unknown_direction() -> None:
    try:
        build_ptz_packet("zoom")
    except ValueError:
        return
    raise AssertionError("Unknown PTZ directions must be rejected.")


def test_ptz_packet_rejects_unknown_head() -> None:
    try:
        build_ptz_packet("up", head="unknown")
    except ValueError:
        return
    raise AssertionError("Unknown PTZ heads must be rejected.")
