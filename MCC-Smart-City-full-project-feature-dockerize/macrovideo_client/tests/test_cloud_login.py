from __future__ import annotations

import os
import sys
from pprint import pprint

from macrovideo.cloud import (
    CloudRequestConfig,
    V380CloudClient,
    build_account_login_request,
    login_account,
)


USERNAME = os.getenv(
    "V380_USERNAME",
    "",
)

PASSWORD = os.getenv(
    "V380_PASSWORD",
    "",
)

API_BASE_URL = os.getenv(
    "V380_API_BASE_URL",
    "https://mapi.av380.net/",
)

VERIFY_TLS = (
    os.getenv(
        "V380_VERIFY_TLS",
        "true",
    ).strip().lower()
    not in {
        "0",
        "false",
        "no",
    }
)


def mask_secret(
    value: str,
    *,
    visible_start: int = 4,
    visible_end: int = 4,
) -> str:
    if not value:
        return "<empty>"

    if len(value) <= visible_start + visible_end:
        return "*" * len(value)

    hidden = len(value) - visible_start - visible_end

    return (
        value[:visible_start]
        + ("*" * hidden)
        + value[-visible_end:]
    )


def main() -> int:
    print("=" * 72)
    print("V380 CLOUD ACCOUNT LOGIN TEST")
    print("=" * 72)

    if not USERNAME:
        print("[!] V380_USERNAME is not configured.")
        return 1

    if not PASSWORD:
        print("[!] V380_PASSWORD is not configured.")
        return 1

    try:
        request = build_account_login_request(
            username=USERNAME,
            password=PASSWORD,
        )

        config = CloudRequestConfig(
            base_url=API_BASE_URL,
            timeout=20.0,
            verify_tls=VERIFY_TLS,
        )

    except ValueError as error:
        print(f"[!] Configuration error: {error}")
        return 1

    print(f"Endpoint: {API_BASE_URL}user/login")
    print(f"Username: {USERNAME}")
    print("Password: <hidden>")
    print(f"Timestamp: {request.timestamp}")
    print(
        "Encrypted password: "
        f"{mask_secret(request.encrypted_password)}"
    )
    print(
        "Signature: "
        f"{mask_secret(request.signature)}"
    )

    printable_document = dict(request.document)
    printable_document["password"] = mask_secret(
        request.encrypted_password
    )
    printable_document["sign"] = mask_secret(
        request.signature
    )

    print("\nOutgoing login JSON:")
    pprint(printable_document)

    try:
        with V380CloudClient(config) as client:
            result = login_account(
                client,
                username=USERNAME,
                password=PASSWORD,
            )

    except TimeoutError as error:
        print(f"[!] Timeout: {error}")
        return 1
    except ConnectionError as error:
        print(f"[!] Connection error: {error}")
        return 1
    except ValueError as error:
        print(f"[!] Invalid response: {error}")
        return 1

    print("\n" + "=" * 72)
    print("LOGIN RESPONSE")
    print("=" * 72)

    print(f"Result: {result.result}")
    print(f"Error code: {result.error_code}")
    print(f"User ID: {result.user_id}")
    print(f"Username: {result.username}")
    print(
        "Access token: "
        f"{mask_secret(result.access_token)}"
    )

    if not result.succeeded:
        print("\n[!] Account login was not accepted.")
        print("\nRaw response:")
        pprint(result.raw_document)
        return 1

    print("\n[+] Account cloud login succeeded.")
    print(
        "[+] The access token can now be passed "
        "directly to the device-list request."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())