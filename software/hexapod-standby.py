#!/usr/bin/env python3
"""Keep the hexapod standing and quietly alive during an active loglm session."""
from __future__ import annotations

import argparse
import random
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from source.hexapod import HexapodRPCClient
from source.hexapod.reactions import perform_reaction


running = True
PRESENCE_REACTIONS = (
    "nod",
    "curious",
    "sway",
    "lean",
    "thinking",
    "tiny_wave",
    "happy",
    "bounce",
    "mission",
)
PRESENCE_WEIGHTS = (4, 4, 4, 4, 3, 3, 2, 2, 2)


def handle_signal(_signum, _frame) -> None:
    global running
    running = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keep the hexapod in a lively standing idle posture.")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between stand keepalive commands.")
    parser.add_argument("--reaction-min", type=float, default=7.0, help="Minimum seconds between idle reactions.")
    parser.add_argument("--reaction-max", type=float, default=13.0, help="Maximum seconds between idle reactions.")
    parser.add_argument("--no-reactions", action="store_true", help="Only keep standing; do not add idle reactions.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable testing.")
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

    rng = random.Random(args.seed)
    client = HexapodRPCClient(socket_path=args.socket)
    safe_call(client, "connect")
    safe_call(client, "servopower", True)
    safe_call(client, "position", 0, 0, 0)

    next_reaction_at = time.monotonic() + _reaction_delay(args, rng)
    keepalive_interval = max(args.interval, 1.0)

    while running:
        now = time.monotonic()
        sleep_for = keepalive_interval
        if not args.no_reactions:
            sleep_for = min(sleep_for, max(next_reaction_at - now, 0.1))
        time.sleep(sleep_for)
        if not running:
            break
        now = time.monotonic()
        if not args.no_reactions and now >= next_reaction_at:
            name = rng.choices(PRESENCE_REACTIONS, weights=PRESENCE_WEIGHTS, k=1)[0]
            try:
                perform_reaction(
                    name,
                    client=client,
                    connect=False,
                    power_on=False,
                    return_to_neutral=True,
                    rng=rng,
                )
            except Exception as exc:
                print(f"hexapod-standby: reaction failed: {exc}", file=sys.stderr)
                safe_call(client, "position", 0, 0, 0)
            next_reaction_at = now + _reaction_delay(args, rng)
        else:
            safe_call(client, "position", 0, 0, 0)

    return 0


def _reaction_delay(args: argparse.Namespace, rng: random.Random) -> float:
    low = max(args.reaction_min, 1.0)
    high = max(args.reaction_max, low)
    return rng.uniform(low, high)


if __name__ == "__main__":
    raise SystemExit(main())
