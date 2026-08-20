from __future__ import annotations

import sys

from macrovideo.gateway.mediamtx_gateway import GatewayConfig, run_gateway


def main() -> int:
    try:
        config = GatewayConfig.from_environment()
    except Exception as exc:
        print(f"[!] Gateway configuration error: {type(exc).__name__}: {exc}")
        return 2

    try:
        return run_gateway(config)
    except ImportError as exc:
        print(f"[!] Missing Python dependency: {exc}")
        print("[!] Run: pip install -r requirements.txt")
        return 3


if __name__ == "__main__":
    sys.exit(main())
