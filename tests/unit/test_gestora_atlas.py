"""Validation of the "La Gestora" atlas and character definition (spec 003: atlas, timing and throw data)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parents[2]
DEF_PATH = ROOT / "assets" / "characters" / "gestora.json"
SOURCE = ROOT / "assets" / "characters" / "bcnfemale.png"
FLOOR_Y = 520                      # index.html: the floor line the grenade lands on


@pytest.fixture(scope="module")
def definition() -> dict:
    return json.loads(DEF_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def atlas(definition) -> pygame.Surface:
    return pygame.image.load(str(ROOT / definition["sheet"]))


def test_frame_table_is_26_poses_plus_the_flying_poop(definition):
    assert len(definition["frames"]) == 27
    assert definition["strips"] == {"walk": [0, 6], "punch": [6, 11], "kick": [11, 16],
                                    "jump": [16, 21], "special": [21, 26], "grenade": [26, 27]}


def test_frames_inside_atlas_and_not_overlapping(definition, atlas):
    bounds = atlas.get_rect()
    rects = [pygame.Rect(f["x"], f["y"], f["w"], f["h"]) for f in definition["frames"]]
    for i, r in enumerate(rects):
        assert r.w > 0 and r.h > 0 and bounds.contains(r), f"frame {i} outside atlas: {tuple(r)}"
        for j in range(i + 1, len(rects)):
            assert not r.colliderect(rects[j]), f"frames {i} and {j} overlap"


def test_atlas_is_transparent_with_no_sheet_gray(definition, atlas):
    assert atlas.get_flags() & pygame.SRCALPHA
    w, h = atlas.get_size()
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        assert atlas.get_at(corner).a == 0, f"corner {corner} is opaque"
    gray = pygame.image.load(str(SOURCE)).get_at((0, 0))
    for i, f in enumerate(definition["frames"]):
        opaque = near_gray = 0
        for y in range(f["y"], f["y"] + f["h"]):
            for x in range(f["x"], f["x"] + f["w"]):
                px = atlas.get_at((x, y))
                if px.a:
                    opaque += 1
                    near_gray += all(abs(px[c] - gray[c]) <= 6 for c in range(3))
        assert opaque / (f["w"] * f["h"]) > 0.10, f"frame {i} is mostly empty"
        assert near_gray / opaque < 0.04, f"frame {i} still contains the sheet's gray background"


def test_anchors_are_inside_frames(definition):
    for i, f in enumerate(definition["frames"]):
        assert 0 <= f["ax"] <= f["w"] and f["fy"] == f["h"], f"frame {i} anchor"


def test_animations_reference_valid_frames(definition):
    n = len(definition["frames"])
    for name, anim in definition["animations"].items():
        assert anim["frames"] and all(0 <= i < n for i in anim["frames"]), name
        if "ticks" in anim:
            assert len(anim["ticks"]) == len(anim["frames"]), name
    for required in ("idle", "walk", "jump", "fall", "punch", "kick", "special", "hit"):
        assert required in definition["animations"]


def test_attack_timing_matches_animation_length(definition):
    for move in ("punch", "kick"):
        a = definition["attacks"][move]
        assert sum(definition["animations"][move]["ticks"]) == a["startup"] + a["active"] + a["recovery"], move


def test_active_window_lands_on_the_extension_frame(definition):
    """The hitbox's active updates must show the extended limb (frame lookup by tick, as in the engine)."""
    def frame_at(move, t):
        acc = 0
        for idx, ticks in zip(definition["animations"][move]["frames"], definition["animations"][move]["ticks"]):
            acc += ticks
            if t < acc:
                return idx
        return definition["animations"][move]["frames"][-1]
    punch, kick = definition["attacks"]["punch"], definition["attacks"]["kick"]
    assert frame_at("punch", punch["startup"] + 1) == 8      # fist fully extended
    assert frame_at("kick", kick["startup"] + 1) == 13       # leg fully extended


def test_special_is_52_updates_and_the_throw_starts_with_the_throwing_pose(definition):
    special = definition["special"]
    ticks = definition["animations"]["special"]["ticks"]
    assert sum(ticks) == 52
    assert special["kind"] == "grenade"
    assert special["launch"] == sum(ticks[:4]), "the poop must leave the hand when the throwing pose (frame 25) starts"
    assert definition["animations"]["special"]["frames"][4] == 25


def test_grenade_arc_is_configured_and_lands_on_the_stage(definition):
    """Ballistics sanity: a launched grenade rises, comes down, and lands within the stage width."""
    gr = definition["special"]["grenade"]
    assert gr["frame"] == 26
    assert 0 < gr["angle"] < 90 and gr["speed"] > 0 and gr["gravity"] > 0
    assert gr["blastRadius"] > 0 and gr["damage"] > 0 and gr["push"] > 0 and gr["blastLife"] > 0
    assert gr["shards"]["count"] > 0 and gr["shards"]["life"] > 0
    vx = gr["speed"] * math.cos(math.radians(gr["angle"]))
    vy = -gr["speed"] * math.sin(math.radians(gr["angle"]))
    y0 = FLOOR_Y + gr["spawn"]["y"]                          # spawn above the floor, at the hand
    assert y0 < FLOOR_Y
    a, b, c = 0.5 * gr["gravity"], vy, -(FLOOR_Y - y0)       # y(n) - FLOOR_Y = a n^2 + b n + c = 0
    flight = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
    assert vy < 0, "the arc must rise first"
    assert 0 < vx * flight < 800, "the arc must land on the stage"
    assert gr["spawn"]["x"] > definition["hurt"]["w"] / 2 + gr["box"]["w"] / 2, "spawn must be clear of the thrower's body"
