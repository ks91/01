"""Small safe hexapod reactions for live research-assistant dialogue."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from .rpc_client import HexapodRPCClient


@dataclass(frozen=True)
class ReactionStep:
    method: str
    args: tuple = ()
    kwargs: dict | None = None
    pause: float = 0.08


@dataclass(frozen=True)
class Reaction:
    name: str
    steps: tuple[ReactionStep, ...]


class DryRunClient:
    """RPC-like client that records calls without touching hardware."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def call(self, method: str, *args, **kwargs):
        self.calls.append((method, args, kwargs))
        print(_format_call(method, args, kwargs))
        return None


NEUTRAL_STEPS = (
    ReactionStep("stop", pause=0.03),
    ReactionStep("balance", (False,), pause=0.03),
    ReactionStep("attitude", (0, 0, 0), pause=0.03),
    ReactionStep("position", (0, 0, 0), pause=0.03),
    ReactionStep("head_horizontal", (90,), pause=0.03),
    ReactionStep("head_vertical", (90,), pause=0.03),
)


REACTIONS: dict[str, Reaction] = {
    "nod": Reaction(
        "nod",
        (
            ReactionStep("head_vertical", (78,), pause=0.12),
            ReactionStep("head_vertical", (98,), pause=0.10),
            ReactionStep("head_vertical", (88,), pause=0.08),
        ),
    ),
    "curious": Reaction(
        "curious",
        (
            ReactionStep("head_horizontal", (72,), pause=0.10),
            ReactionStep("attitude", (0, 4, -5), pause=0.14),
            ReactionStep("head_horizontal", (108,), pause=0.12),
            ReactionStep("attitude", (0, -2, 4), pause=0.10),
        ),
    ),
    "surprised": Reaction(
        "surprised",
        (
            ReactionStep("position", (0, -8, 5), pause=0.10),
            ReactionStep("head_vertical", (112,), pause=0.12),
            ReactionStep("position", (0, 0, 0), pause=0.08),
            ReactionStep("head_vertical", (88,), pause=0.08),
        ),
    ),
    "thinking": Reaction(
        "thinking",
        (
            ReactionStep("head_horizontal", (68,), pause=0.16),
            ReactionStep("head_horizontal", (112,), pause=0.18),
            ReactionStep("head_horizontal", (84,), pause=0.10),
        ),
    ),
    "happy": Reaction(
        "happy",
        (
            ReactionStep("attitude", (5, 0, 5), pause=0.09),
            ReactionStep("attitude", (-5, 0, -5), pause=0.09),
            ReactionStep("attitude", (4, 0, 4), pause=0.08),
        ),
    ),
    "tiny_wave": Reaction(
        "tiny_wave",
        (
            ReactionStep("head_horizontal", (65,), pause=0.08),
            ReactionStep("head_horizontal", (115,), pause=0.08),
            ReactionStep("head_horizontal", (75,), pause=0.08),
            ReactionStep("head_horizontal", (105,), pause=0.08),
        ),
    ),
    "mission": Reaction(
        "mission",
        (
            ReactionStep("position", (0, 5, 4), pause=0.10),
            ReactionStep("head_vertical", (82,), pause=0.08),
            ReactionStep("position", (0, 0, 0), pause=0.08),
        ),
    ),
}


DEFAULT_WEIGHTS: dict[str, int] = {
    "nod": 3,
    "curious": 3,
    "thinking": 2,
    "happy": 2,
    "tiny_wave": 2,
    "mission": 2,
    "surprised": 1,
}


def available_reactions() -> list[str]:
    return sorted(REACTIONS)


def random_reaction_name(rng: random.Random | None = None) -> str:
    rng = rng or random
    names = list(DEFAULT_WEIGHTS)
    weights = [DEFAULT_WEIGHTS[name] for name in names]
    return rng.choices(names, weights=weights, k=1)[0]


def perform_reaction(
    name: str | None = None,
    *,
    client: HexapodRPCClient | DryRunClient | None = None,
    connect: bool = True,
    power_on: bool = True,
    return_to_neutral: bool = True,
    power_off: bool = False,
    rng: random.Random | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Perform one short safe reaction and return the reaction name."""

    client = client or HexapodRPCClient()
    reaction_name = name or random_reaction_name(rng)
    if reaction_name == "random":
        reaction_name = random_reaction_name(rng)
    if reaction_name not in REACTIONS:
        choices = ", ".join(available_reactions())
        raise ValueError(f"Unknown reaction '{reaction_name}'. Available: {choices}")

    if connect:
        _safe_call(client, "connect")
    if power_on:
        _safe_call(client, "servopower", True)
        sleep(0.05)

    try:
        _run_steps(client, REACTIONS[reaction_name].steps, sleep=sleep)
    finally:
        _safe_call(client, "stop")
        if return_to_neutral:
            _run_steps(client, NEUTRAL_STEPS, sleep=sleep)
        if power_off:
            _safe_call(client, "servopower", False)

    return reaction_name


def _run_steps(
    client: HexapodRPCClient | DryRunClient,
    steps: Iterable[ReactionStep],
    *,
    sleep: Callable[[float], None],
) -> None:
    for step in steps:
        kwargs = step.kwargs or {}
        client.call(step.method, *step.args, **kwargs)
        if step.pause > 0:
            sleep(step.pause)


def _safe_call(client: HexapodRPCClient | DryRunClient, method: str, *args, **kwargs) -> None:
    try:
        client.call(method, *args, **kwargs)
    except Exception:
        if method in {"stop", "servopower"}:
            raise


def _format_call(method: str, args: tuple, kwargs: dict) -> str:
    parts = [repr(arg) for arg in args]
    parts.extend(f"{key}={value!r}" for key, value in kwargs.items())
    return f"hexapod.call({method!r}{', ' if parts else ''}{', '.join(parts)})"
