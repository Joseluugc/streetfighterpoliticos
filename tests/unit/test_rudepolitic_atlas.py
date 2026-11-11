"""Validation of the "Rude Politic" atlas and character definition (spec 002: SC-1..SC-4)."""
from __future__ import annotations

import json
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parents[2]
DEF_PATH = ROOT / "assets" / "characters" / "rudepolitic.json"
SOURCE = ROOT / "assets" / "rudepolitic.png"


@pytest.fixture(scope="module")
def definition() -> dict:
    return json.loads(DEF_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def atlas(definition) -> pygame.Surface:
    return pygame.image.load(str(ROOT / definition["sheet"]))


def test_has_26_frames_in_five_strips(definition):
    assert len(definition["frames"]) == 26
    assert definition["strips"] == {"walk": [0, 6], "punch": [6, 11], "kick": [11, 16], "jump": [16, 21], "special": [21, 26]}


def test_frames_inside_atlas_and_not_overlapping(definition, atlas):
    bounds = atlas.get_rect()
    rects = [pygame.Rect(f["x"], f["y"], f["w"], f["h"]) for f in definition["frames"]]
    for i, r in enumerate(rects):
        assert r.w > 0 and r.h > 0 and bounds.contains(r), f"frame {i} outside atlas: {tuple(r)}"
        for j in range(i + 1, len(rects)):
            assert not r.colliderect(rects[j]), f"frames {i} and {j} overlap"


def test_atlas_is_transparent_with_no_sheet_gray_or_labels(definition, atlas):
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
        assert opaque / (f["w"] * f["h"]) > 0.15, f"frame {i} is mostly empty"
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
    """The state ends exactly when its animation does (no stuck or truncated animation)."""
    for move in ("punch", "kick", "special"):
        a = definition["attacks"][move]
        assert sum(definition["animations"][move]["ticks"]) == a["startup"] + a["active"] + a["recovery"], move


def test_special_is_stronger_than_basics_and_not_clashable(definition):
    atk = definition["attacks"]
    assert atk["special"]["damage"] >= 2 * atk["kick"]["damage"] > 2 * atk["punch"]["damage"] * 0.6
    assert atk["special"]["clash"] is False
    assert definition["special"] == {"name": "Golpe Español", "kind": "melee", "airOk": True, "impactReach": 110}
    assert sum(definition["animations"]["special"]["ticks"]) == 52


def test_active_window_lands_on_the_extension_frame(definition):
    """Hitbox frames must show the extended pose, not the wind-up (frame lookup by tick)."""
    def frame_at(move, t):
        acc = 0
        for idx, ticks in zip(definition["animations"][move]["frames"], definition["animations"][move]["ticks"]):
            acc += ticks
            if t < acc:
                return idx
        return definition["animations"][move]["frames"][-1]
    assert frame_at("punch", 10) == 9           # full-extension punch pose
    assert frame_at("kick", 12) == 13           # leg fully extended
    assert frame_at("special", 28) == 24        # flag striking the floor
