from __future__ import annotations

import getpass
import os
import sys
import time

from macrovideo.protocol.legacy_lan_login import (
    perform_legacy_lan_login,
)
from macrovideo.protocol.legacy_live_client import (
    LegacyV2LiveClient,
)
from macrovideo.protocol.legacy_live_stream import (
    LegacyLiveSession,
)


CAMERA_HOST = os.getenv(
    "V380_CAMERA_HOST",
    "192.2.42.100",
).strip()

CAMERA_PORT = int(
    os.getenv(
        "V380_CAMERA_PORT",
        "8800",
    )
)

DEVICE_ID = int(
    os.getenv(
        "V380_DEVICE_ID",
        "105848032",
    )
)

CAMERA_USERNAME = os.getenv(
    "V380_CAMERA_USERNAME",
    "admin",
).strip()

WINDOW_TITLE = os.getenv(
    "V380_LIVE_WINDOW_TITLE",
    "V380 Live View",
)

MAX_SECONDS = float(
    os.getenv(
        "V380_LIVE_MAX_SECONDS",
        "0",
    )
)

SOCKET_TIMEOUT = float(
    os.getenv(
        "V380_LIVE_SOCKET_TIMEOUT",
        "2",
    )
)

IDLE_TIMEOUT = float(
    os.getenv(
        "V380_LIVE_IDLE_TIMEOUT",
        "20",
    )
)

RECONNECT_DELAY = float(
    os.getenv(
        "V380_LIVE_RECONNECT_DELAY",
        "2",
    )
)

MAX_RECONNECTS = int(
    os.getenv(
        "V380_LIVE_MAX_RECONNECTS",
        "0",
    )
)


def resolve_camera_password() -> str:
    configured = os.getenv(
        "V380_CAMERA_PASSWORD",
        "",
    )

    if configured:
        return configured

    return getpass.getpass(
        "Camera password: "
    )


def open_camera_session(
    *,
    password: str,
) -> tuple[
    LegacyV2LiveClient,
    object,
]:
    print(
        "\nSTEP 1: LEGACY LAN LOGIN"
    )

    login_exchange = (
        perform_legacy_lan_login(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            device_id=DEVICE_ID,
            username=CAMERA_USERNAME,
            password=password,
        )
    )

    login = login_exchange.response

    if not login.succeeded:
        raise PermissionError(
            "Camera rejected the LAN login."
        )

    print(
        "[+] LAN authentication succeeded."
    )
    print(
        f"[+] Fresh login handle: "
        f"{login.handle}"
    )
    print(
        f"[+] Token session: "
        f"{login.token_session}"
    )
    print(
        f"[+] Protocol version: "
        f"{login.protocol_version}"
    )

    session = LegacyLiveSession(
        device_id=DEVICE_ID,
        login_handle=login.handle,
        token_session=login.token_session,
        protocol_version=(
            login.protocol_version
        ),
    )

    print(
        "\nSTEP 2: OPEN LIVE MEDIA STREAM"
    )

    client = LegacyV2LiveClient(
        host=CAMERA_HOST,
        port=CAMERA_PORT,
        session=session,
        socket_timeout=SOCKET_TIMEOUT,
        idle_timeout=IDLE_TIMEOUT,
    )

    response = client.connect()

    print(
        "[+] Camera accepted the live stream."
    )
    print(
        f"[+] Camera stream metadata: "
        f"{response.width}x"
        f"{response.height}"
    )

    return client, response


def main() -> int:
    try:
        import av
    except ImportError:
        print(
            "[!] PyAV is not installed."
        )
        print(
            "Run: pip install -r requirements.txt"
        )
        return 1

    try:
        import cv2
    except ImportError:
        print(
            "[!] OpenCV is not installed."
        )
        print(
            "Run: pip install -r requirements.txt"
        )
        return 1

    print("=" * 72)
    print(
        "V380 RESILIENT DIRECT LAN LIVE VIEW"
    )
    print("=" * 72)
    print(
        "Pipeline: LAN login -> 301 -> 303 "
        "-> reassemble -> AES decrypt "
        "-> H.265 -> OpenCV"
    )
    print(
        "Temporary TCP timeouts are tolerated; "
        "real session loss triggers a fresh login "
        "and automatic reconnect."
    )

    password = resolve_camera_password()

    total_displayed = 0
    total_decoded = 0
    total_connections = 0
    reconnect_count = 0

    application_start = time.monotonic()
    stop_requested = False

    while not stop_requested:
        client: LegacyV2LiveClient | None = None

        try:
            client, _ = open_camera_session(
                password=password,
            )
            total_connections += 1

            # A fresh decoder is important after every reconnect because
            # the HEVC parameter-set/keyframe state belongs to one stream
            # session.
            codec = av.CodecContext.create(
                "hevc",
                "r",
            )

            session_displayed = 0
            session_decoded = 0
            session_start = time.monotonic()
            last_report = session_start

            print(
                "\nSTEP 3: DECODE H.265 IN REAL TIME"
            )
            print(
                "[+] Press Q or ESC in the "
                "video window to stop."
            )

            for _, hevc_payload in (
                client.iter_hevc_payloads()
            ):
                packets = codec.parse(
                    hevc_payload
                )

                for packet in packets:
                    frames = codec.decode(
                        packet
                    )

                    for video_frame in frames:
                        session_decoded += 1
                        total_decoded += 1

                        image = (
                            video_frame.to_ndarray(
                                format="bgr24"
                            )
                        )

                        cv2.imshow(
                            WINDOW_TITLE,
                            image,
                        )

                        session_displayed += 1
                        total_displayed += 1

                        key = (
                            cv2.waitKey(1)
                            & 0xFF
                        )

                        if key in {
                            ord("q"),
                            27,
                        }:
                            print(
                                "[LIVE] Stop requested "
                                "from keyboard."
                            )
                            stop_requested = True
                            break

                    if stop_requested:
                        break

                if stop_requested:
                    break

                now = time.monotonic()

                if (
                    now - last_report
                    >= 1.0
                ):
                    stats = client.stats
                    elapsed = max(
                        now - session_start,
                        0.001,
                    )
                    fps = (
                        session_displayed
                        / elapsed
                    )

                    print(
                        "[LIVE] "
                        f"displayed={session_displayed}, "
                        f"decoded={session_decoded}, "
                        f"fps={fps:.1f}, "
                        f"transport="
                        f"{stats.transport_fragments}, "
                        f"frames="
                        f"{stats.complete_frames}, "
                        f"video="
                        f"{stats.video_frames}, "
                        f"other="
                        f"{stats.non_video_frames}"
                    )

                    last_report = now

                if (
                    MAX_SECONDS > 0
                    and (
                        now - application_start
                        >= MAX_SECONDS
                    )
                ):
                    print(
                        "[LIVE] Maximum application "
                        "runtime reached."
                    )
                    stop_requested = True
                    break

            # A normal iterator exit is unusual for a live socket.
            if not stop_requested:
                raise ConnectionError(
                    "Live-media iterator ended "
                    "without a user stop request."
                )

        except KeyboardInterrupt:
            print(
                "\n[LIVE] Interrupted by user."
            )
            stop_requested = True

        except (
            TimeoutError,
            ConnectionError,
            ConnectionResetError,
            BrokenPipeError,
            OSError,
            ValueError,
        ) as error:
            if stop_requested:
                break

            reconnect_count += 1

            print(
                "\n[RECONNECT] Live session lost: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            if (
                MAX_RECONNECTS > 0
                and reconnect_count
                > MAX_RECONNECTS
            ):
                print(
                    "[!] Maximum reconnect count "
                    "reached."
                )
                stop_requested = True
                break

            print(
                "[RECONNECT] Closing the old "
                "session and obtaining a fresh "
                "LAN login handle."
            )
            print(
                "[RECONNECT] Retry "
                f"{reconnect_count} in "
                f"{RECONNECT_DELAY:.1f}s..."
            )

            # Keep the OpenCV window responsive during the delay.
            delay_end = (
                time.monotonic()
                + RECONNECT_DELAY
            )

            while (
                time.monotonic()
                < delay_end
            ):
                key = (
                    cv2.waitKey(50)
                    & 0xFF
                )

                if key in {
                    ord("q"),
                    27,
                }:
                    stop_requested = True
                    break

                time.sleep(0.05)

        except PermissionError as error:
            print(
                "[!] Authentication/session "
                f"permission error: {error}"
            )
            stop_requested = True

        except Exception as error:
            print(
                "[!] Non-recoverable live-view "
                f"error: {type(error).__name__}: "
                f"{error}"
            )
            stop_requested = True

        finally:
            if client is not None:
                stats = client.stats

                print(
                    "\n[SESSION] "
                    f"transport="
                    f"{stats.transport_fragments}, "
                    f"frames="
                    f"{stats.complete_frames}, "
                    f"video="
                    f"{stats.video_frames}, "
                    f"other="
                    f"{stats.non_video_frames}"
                )

                client.close()

    cv2.destroyAllWindows()

    elapsed = max(
        time.monotonic()
        - application_start,
        0.001,
    )

    print(
        "\n" + "=" * 72
    )
    print(
        "LIVE VIEW APPLICATION COMPLETE"
    )
    print(
        "=" * 72
    )
    print(
        f"Connections opened: "
        f"{total_connections}"
    )
    print(
        f"Automatic reconnects: "
        f"{reconnect_count}"
    )
    print(
        f"Decoded HEVC frames: "
        f"{total_decoded}"
    )
    print(
        f"Displayed frames: "
        f"{total_displayed}"
    )
    print(
        f"Total runtime: "
        f"{elapsed:.1f}s"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
