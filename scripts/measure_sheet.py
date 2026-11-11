"""Measure the 9 frames of the character sheet and print the `frames` JSON for dummy.json.

Usage: python scripts/measure_sheet.py assets/characters/dummy.png

Frame search windows (x0, x1, y0, y1) are the hand-chosen areas that contain exactly one pose each
(the sheet is 5 poses on the top row and 4 on the bottom row, plus the scroll projectile).
Each frame is cropped to the tight bounding box of non-background pixels. `anchor_x` is the
horizontal point that should sit on the fighter's x (head centre for upright poses, box centre for
airborne poses) and `foot_y` is the box bottom (the floor line).
"""
from __future__ import annotations

import json
import sys

import pygame

WINDOWS = [
    (0, 225, 0, 305),      # 1 idle A
    (225, 420, 0, 305),    # 2 idle B
    (420, 600, 0, 305),    # 3 walk
    (600, 765, 0, 305),    # 4 jump
    (765, 1024, 0, 305),   # 5 fall
    (0, 246, 306, 572),    # 6 punch
    (246, 462, 306, 572),  # 7 kick
    (462, 625, 306, 572),  # 8 guard
    (625, 855, 306, 572),  # 9 special cast (fighter only)
]
PROJECTILE_WINDOW = (855, 1024, 306, 572)
AIRBORNE = {3, 4}  # zero-based indices that use the box centre as anchor


def main(path: str, tol: int = 28) -> None:
    sheet = pygame.image.load(path)
    bg = sheet.get_at((0, 0))[:3]

    def is_fg(x: int, y: int) -> bool:
        p = sheet.get_at((x, y))
        return any(abs(p[i] - bg[i]) > tol for i in range(3))

    def bbox(win: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x0, x1, y0, y1 = win
        pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if is_fg(x, y)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    frames = []
    for i, win in enumerate(WINDOWS):
        left, top, right, bottom = bbox(win)
        if i in AIRBORNE:
            anchor_x = (right - left) // 2
        else:
            head = [x for y in range(top, top + max(8, (bottom - top) // 8))
                    for x in range(left, right) if is_fg(x, y)]
            anchor_x = round(sum(head) / len(head)) - left
        frames.append({"x": left, "y": top, "w": right - left, "h": bottom - top,
                       "anchor_x": anchor_x, "foot_y": bottom - top})
    left, top, right, bottom = bbox(PROJECTILE_WINDOW)
    proj = {"x": left, "y": top, "w": right - left, "h": bottom - top}
    print(json.dumps({"frames": frames, "projectile_sprite": proj}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets/characters/dummy.png")
