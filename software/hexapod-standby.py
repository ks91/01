#!/usr/bin/env python3
"""Keep the hexapod standing while an active loglm session is running."""
from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from source.hexapod import HexapodRPCClient


running = True


def handle_signal(_signum, _frame) -> None:
    global running
    running = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keep the hexapod in a standing idle posture.")
    parser.add_argument("--interval", type=float, default=6.0, help="Seconds between stand keepalive commands.")
    parser.add_argument("--socket", default=None, help="Override HEXAPOD_RPC_SOCKET.")
    return parser.parse_args()


def safe_call(client: HexapodRPCClient, method: str, *args) -> None:
    try:
        client.call(method, *args)
    except Exception as exc:
        print(f"hexapod-standby: {method} failed: {exc}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    client = HexapodRPCClient(socket_path=args.socket)
    safe_call(client, "connect")
    safe_call(client, "servopower", True)
    safe_call(client, "position", 0, 0, 0)

    while running:
        time.sleep(max(args.interval, 1.0))
        if not running:
            break
        safe_call(client, "position", 0, 0, 0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
