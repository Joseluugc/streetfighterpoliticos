"""Static settings and the data-driven character configuration loader."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOGICAL_WIDTH = 1024
LOGICAL_HEIGHT = 572
FLOOR_Y = 520
STAGE_LEFT = 0
STAGE_RIGHT = 1024
UPDATES_PER_SECOND = 60
MAX_CATCHUP_STEPS = 5

CHARACTER_CONFIG_PATH = PROJECT_ROOT / "assets" / "characters" / "dummy.json"


class ConfigError(Exception):
    """Raised when a configuration file is missing or invalid (message names the file)."""


@dataclass(frozen=True, slots=True)
class Stage:
    left: int = STAGE_LEFT
    right: int = STAGE_RIGHT
    floor_y: int = FLOOR_Y


@dataclass(frozen=True, slots=True)
class KeyScheme:
    left: int = pygame.K_a
    right: int = pygame.K_d
    jump: int = pygame.K_w
    punch: int = pygame.K_j
    kick: int = pygame.K_k
    guard: int = pygame.K_l
    special: int = pygame.K_i
    debug_toggle: int = pygame.K_F1
    training_punch: int = pygame.K_1
    training_kick: int = pygame.K_2
    training_guard: int = pygame.K_3
    training_special: int = pygame.K_4


@dataclass(frozen=True, slots=True)
class BoxConfig:
    w: int
    h: int
    offset_x: int = 0
    offset_y: int = 0


@dataclass(frozen=True, slots=True)
class FrameRect:
    x: int
    y: int
    w: int
    h: int
    anchor_x: int
    foot_y: int


@dataclass(frozen=True, slots=True)
class AttackConfig:
    startup: int
    active: int
    recovery: int
    damage: int
    knockback: int
    box: BoxConfig

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery


@dataclass(frozen=True, slots=True)
class ProjectileConfig:
    speed: float
    lifetime: int
    damage: int
    knockback: int
    box: BoxConfig
    spawn_x: int
    spawn_y: int


@dataclass(frozen=True, slots=True)
class SpecialConfig:
    startup: int
    recovery: int
    projectile: ProjectileConfig

    @property
    def total(self) -> int:
        return self.startup + self.recovery


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    name: str
    sheet_path: Path
    background_path: Path
    background_tolerance: int
    sprite_scale: float
    frames: tuple[FrameRect, ...]
    projectile_sprite: tuple[int, int, int, int]
    animations: dict[str, tuple[int, ...]]
    idle_frame_hold: int
    walk_speed: float
    jump_velocity: float
    gravity: float
    hurtbox: BoxConfig
    punch: AttackConfig
    kick: AttackConfig
    special: SpecialConfig
    hitstun: int
    blockstun: int
    max_health: int


def _box(d: dict[str, Any]) -> BoxConfig:
    return BoxConfig(int(d["w"]), int(d["h"]), int(d.get("offset_x", 0)), int(d.get("offset_y", 0)))


def _attack(d: dict[str, Any]) -> AttackConfig:
    return AttackConfig(int(d["startup"]), int(d["active"]), int(d["recovery"]),
                        int(d["damage"]), int(d["knockback"]), _box(d["box"]))


def load_character_config(path: str | Path = CHARACTER_CONFIG_PATH) -> CharacterConfig:
    """Load and validate a character JSON file. Raises ConfigError naming the file."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Character config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    try:
        proj = raw["special"]["projectile"]
        ps = raw["projectile_sprite"]
        return CharacterConfig(
            name=raw["name"],
            sheet_path=PROJECT_ROOT / raw["sheet"],
            background_path=PROJECT_ROOT / raw["background"],
            background_tolerance=int(raw["background_tolerance"]),
            sprite_scale=float(raw["sprite_scale"]),
            frames=tuple(FrameRect(int(f["x"]), int(f["y"]), int(f["w"]), int(f["h"]),
                                   int(f["anchor_x"]), int(f["foot_y"])) for f in raw["frames"]),
            projectile_sprite=(int(ps["x"]), int(ps["y"]), int(ps["w"]), int(ps["h"])),
            animations={k: tuple(int(i) for i in v) for k, v in raw["animations"].items()},
            idle_frame_hold=int(raw["idle_frame_hold"]),
            walk_speed=float(raw["walk_speed"]),
            jump_velocity=float(raw["jump_velocity"]),
            gravity=float(raw["gravity"]),
            hurtbox=_box(raw["hurtbox"]),
            punch=_attack(raw["attacks"]["PUNCH"]),
            kick=_attack(raw["attacks"]["KICK"]),
            special=SpecialConfig(
                int(raw["special"]["startup"]), int(raw["special"]["recovery"]),
                ProjectileConfig(float(proj["speed"]), int(proj["lifetime"]), int(proj["damage"]),
                                 int(proj["knockback"]), _box(proj["box"]),
                                 int(proj["spawn_offset"]["x"]), int(proj["spawn_offset"]["y"]))),
            hitstun=int(raw["hitstun"]),
            blockstun=int(raw["blockstun"]),
            max_health=int(raw["max_health"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Missing or invalid key {exc} in {path}") from exc
