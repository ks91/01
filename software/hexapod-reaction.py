#!/usr/bin/env python3
"""Run a small hexapod reaction through the RPC bridge."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from source.hexapod.reactions import DryRunClient, available_reactions, perform_reaction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small safe hexapod reaction.")
    parser.add_argument(
        "reaction",
        nargs="?",
        default="random",
        help="Reaction name. Use 'random' or one of: " + ", ".join(available_reactions()),
    )
    parser.add_argument("--dry-run", action="store_true", help="Print RPC calls without touching hardware.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable testing.")
    parser.add_argument("--no-connect", action="store_true", help="Do not call connect first.")
    parser.add_argument("--no-power-on", action="store_true", help="Do not turn servo power on first.")
    parser.add_argument("--no-neutral", action="store_true", help="Do not return to neutral posture.")
    parser.add_argument("--power-off", action="store_true", help="Turn servo power off after the reaction.")
    parser.add_argument("--list", action="store_true", help="List available reaction names and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for name in available_reactions():
            print(name)
        return

    rng = random.Random(args.seed) if args.seed is not None else None
    client = DryRunClient() if args.dry_run else None
    reaction_name = perform_reaction(
        args.reaction,
        client=client,
        connect=not args.no_connect,
        power_on=not args.no_power_on,
        return_to_neutral=not args.no_neutral,
        power_off=args.power_off,
        rng=rng,
    )
    print(f"reaction: {reaction_name}")


if __name__ == "__main__":
    main()
