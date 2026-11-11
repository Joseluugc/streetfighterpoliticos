"""Fighter finite state machine definition: states, per-state specs and legal transitions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class FighterState(Enum):
    IDLE = auto()
    WALKING = auto()
    JUMPING = auto()
    FALLING = auto()
    PUNCHING = auto()
    KICKING = auto()
    DEFENDING = auto()
    SPECIAL = auto()
    HIT_STUN = auto()


S = FighterState


@dataclass(frozen=True, slots=True)
class StateSpec:
    """Static description of a state. `frames` are zero-based sheet indices (one animation)."""
    frames: tuple[int, ...]
    interruptible: bool
    next: frozenset[FighterState]


_FREE = frozenset({S.WALKING, S.IDLE, S.JUMPING, S.PUNCHING, S.KICKING, S.DEFENDING, S.SPECIAL, S.HIT_STUN})

STATE_TABLE: dict[FighterState, StateSpec] = {
    S.IDLE: StateSpec((0, 1), True, _FREE),
    S.WALKING: StateSpec((2,), True, _FREE),
    S.JUMPING: StateSpec((3,), False, frozenset({S.FALLING, S.HIT_STUN})),
    S.FALLING: StateSpec((4,), False, frozenset({S.IDLE, S.WALKING, S.HIT_STUN})),
    S.PUNCHING: StateSpec((5,), False, frozenset({S.IDLE, S.HIT_STUN})),
    S.KICKING: StateSpec((6,), False, frozenset({S.IDLE, S.HIT_STUN})),
    S.DEFENDING: StateSpec((7,), True, frozenset({S.IDLE, S.WALKING, S.HIT_STUN})),
    S.SPECIAL: StateSpec((8,), False, frozenset({S.IDLE, S.HIT_STUN})),
    S.HIT_STUN: StateSpec((0,), False, frozenset({S.IDLE, S.FALLING})),
}
