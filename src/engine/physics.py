"""Hitbox/Hurtbox types and pure collision resolution (no drawing, no clock)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import pygame


@dataclass(slots=True)
class Hurtbox:
    """Where a fighter can be hit. Carries no attack data."""
    rect: pygame.Rect
    owner_id: int


@dataclass(slots=True)
class Hitbox:
    """Attack payload. Exists only during an attack's active frames."""
    rect: pygame.Rect
    owner_id: int
    damage: int
    knockback: int
    hitstun: int
    blockstun: int
    already_hit: set[int] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class HitEvent:
    attacker_id: int
    defender_id: int
    hitbox: Hitbox
    blocked: bool


def place_box(x: float, y: float, facing: int, w: int, h: int,
              offset_x: int, offset_y: int) -> pygame.Rect:
    """World rect for a box relative to a feet-centre point.

    `offset_x` is the distance from `x` to the box's near edge in the facing direction (mirrored
    by `facing`); `offset_y` is the box top relative to the feet (negative = above).
    """
    left = x + offset_x if facing >= 0 else x - offset_x - w
    return pygame.Rect(round(left), round(y + offset_y), w, h)


def resolve_hits(hitboxes: Sequence[Hitbox], hurtboxes: Sequence[Hurtbox],
                 is_blocking: Callable[[int, Hitbox], bool]) -> list[HitEvent]:
    """Test each hitbox against the *opposing* hurtboxes only; each hitbox hits a target once."""
    events: list[HitEvent] = []
    for hit in hitboxes:
        for hurt in hurtboxes:
            if hurt.owner_id == hit.owner_id or hurt.owner_id in hit.already_hit:
                continue
            if hit.rect.colliderect(hurt.rect):
                hit.already_hit.add(hurt.owner_id)
                events.append(HitEvent(hit.owner_id, hurt.owner_id, hit, is_blocking(hurt.owner_id, hit)))
    return events
