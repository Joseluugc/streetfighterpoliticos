"""Slice a character sprite sheet into a clean, transparent atlas for the browser game.

Usage: python scripts/build_character_atlas.py [rudepolitic | gestora | all]

Each entry of CHARACTERS describes one sheet: where it is, where the atlas and the character
definition go, and the hand-chosen window of every animation strip. Outputs:
    <atlas>       RGBA atlas, one pose per cell, no gray, no labels, no bleed
    <definition>  its "frames" and "strips" keys are (re)written; every other key (animations,
                  attacks, special, ...) is kept as authored.

Inside a strip window the poses are the connected foreground components; poses that touch are cut
at their emptiest column. A pose is cut out by its OWN pixels (not by its bounding rectangle), so
overlapping rectangles cannot leak into each other. A strip with count 1 is one sprite made of every
piece inside its window (used for the flying poop of the "gestora" special). `ax` is the median x of
the hips/thighs (the planted part, so the body doesn't slide between poses) and `fy` the bottom of
the pose (the floor line).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent

TOL = 28            # distance from the sheet's gray that still counts as background
MIN_AREA = 150      # components smaller than this are "specks" (sparks, a fingertip): attached to the nearest pose
HOLE_MAX = 250      # enclosed background-coloured pockets up to this many px are suit highlights (kept opaque)
SPECK_MIN = 12      # ...unless they are tiny noise
PAD = 2             # transparent margin between atlas cells


@dataclass(frozen=True)
class Sheet:
    source: str                              # gray-background sheet (1536x1024)
    atlas: str                               # output RGBA atlas
    definition: str                          # character JSON (frames/strips are rewritten)
    strips: dict[str, tuple[int, int, int, int, int]]   # name: (x0, x1, y0, y1, pose count)
    labels: list[tuple[int, int, int, int]]  # (x, y, w, h) of the dark text labels, blanked before measuring


CHARACTERS: dict[str, Sheet] = {
    "rudepolitic": Sheet(
        source="assets/rudepolitic.png",
        atlas="assets/characters/rudepolitic.png",
        definition="assets/characters/rudepolitic.json",
        strips={
            "walk":    (0, 1536, 55, 330, 6),
            "punch":   (0, 805, 380, 640, 5),
            "kick":    (810, 1536, 380, 640, 5),
            "jump":    (0, 810, 640, 1000, 5),
            "special": (810, 1536, 695, 1000, 5),
        },
        labels=[(14, 16, 205, 35), (14, 338, 165, 34), (833, 338, 118, 34), (14, 656, 104, 44), (814, 656, 415, 44)],
    ),
    "gestora": Sheet(
        source="assets/characters/bcnfemale.png",
        atlas="assets/characters/gestora.png",
        definition="assets/characters/gestora.json",
        strips={
            "walk":    (0, 1536, 55, 330, 6),
            "punch":   (0, 805, 380, 640, 5),
            "kick":    (810, 1536, 380, 640, 5),
            "jump":    (0, 810, 640, 1000, 5),
            # the special strip stops before the flying poop (cut out as its own sprite below)
            "special": (810, 1412, 695, 1000, 5),
            "grenade": (1412, 1536, 740, 850, 1),
        },
        labels=[(14, 16, 205, 36), (14, 343, 160, 39), (830, 343, 122, 39), (14, 661, 106, 39), (829, 663, 460, 37)],
    ),
}


def pose_masks(fg: pygame.mask.Mask, win: pygame.Rect, n: int) -> list[pygame.mask.Mask]:
    """Return `n` full-sheet-sized masks, one per pose of the strip window, left to right."""
    region = pygame.mask.Mask(fg.get_size())
    for y in range(win.y, win.bottom):                      # intersect fg with the window
        for x in range(win.x, win.right):
            if fg.get_at((x, y)):
                region.set_at((x, y), 1)
    if n == 1:                                              # one sprite: everything in the window
        return [region]
    comps = [c for c in region.connected_components(SPECK_MIN)]
    big = [c for c in comps if c.count() >= MIN_AREA]
    small = [c for c in comps if c.count() < MIN_AREA]
    big.sort(key=lambda c: c.get_bounding_rects()[0].x)
    while len(big) < n:                                     # touching poses: cut the widest one apart
        widest = max(big, key=lambda c: c.get_bounding_rects()[0].w)
        r = widest.get_bounding_rects()[0]
        lo, hi = r.x + r.w * 3 // 10, r.x + r.w * 7 // 10
        cut = min(range(lo, hi), key=lambda x: sum(widest.get_at((x, y)) for y in range(r.y, r.bottom)))
        left, right = pygame.mask.Mask(fg.get_size()), pygame.mask.Mask(fg.get_size())
        for y in range(r.y, r.bottom):
            for x in range(r.x, r.right):
                if widest.get_at((x, y)):
                    (left if x < cut else right).set_at((x, y), 1)
        big.remove(widest)
        big += [left, right]
        big.sort(key=lambda c: c.get_bounding_rects()[0].x)
    if len(big) != n:
        raise SystemExit(f"strip window {tuple(win)}: expected {n} poses, found {len(big)}")
    for sp in small:                                        # attach sparks / fingertips to the closest pose
        c = sp.get_bounding_rects()[0].center
        owner = min(big, key=lambda m: min(abs(c[0] - r.centerx) + abs(c[1] - r.centery) for r in m.get_bounding_rects()[:1]))
        owner.draw(sp, (0, 0))
    return big


def build(name: str, sheet: Sheet) -> None:
    src, atlas_path, def_path = ROOT / sheet.source, ROOT / sheet.atlas, ROOT / sheet.definition
    image = pygame.image.load(str(src))
    rgba = pygame.Surface(image.get_size(), pygame.SRCALPHA)   # same pixel format as the RGBA mask surface
    rgba.blit(image, (0, 0))
    bg = image.get_at((0, 0))
    bgm = pygame.mask.from_threshold(image, bg, (TOL, TOL, TOL, 255))
    w, h = image.get_size()
    fg = pygame.mask.Mask((w, h), fill=True)
    for comp in bgm.connected_components():                 # background = gray regions touching the sheet edge;
        r = comp.get_bounding_rects()[0]                    # small gray-ish pixels enclosed by the suit stay opaque;
        if r.x == 0 or r.y == 0 or r.right == w or r.bottom == h or comp.count() > HOLE_MAX:   # big enclosed pockets
            fg.erase(comp, (0, 0))                          # (between the legs, around dust) are background too
    for lx, ly, lw, lh in sheet.labels:
        fg.erase(pygame.mask.Mask((lw, lh), fill=True), (lx, ly))

    cells: list[tuple[str, pygame.Surface, int]] = []       # (strip, RGBA cell, hip x within cell)
    for strip, (x0, x1, y0, y1, n) in sheet.strips.items():
        for m in pose_masks(fg, pygame.Rect(x0, y0, x1 - x0, y1 - y0), n):
            box = m.get_bounding_rects()
            r = box[0].unionall(box[1:])
            cell = m.to_surface(setsurface=rgba, unsetcolor=(0, 0, 0, 0)).subsurface(r).copy()
            band = range(r.y + r.h // 2, r.y + r.h * 9 // 10)      # hips / thighs: the part that stays planted
            xs = sorted(x - r.x for y in band for x in range(r.x, r.right)
                        if m.get_at((x, y)) and sum(image.get_at((x, y))[:3]) < 330)   # dark suit pixels only
            ax = xs[len(xs) // 2] if xs else r.w // 2
            cells.append((strip, cell, ax))

    # pack: one row per strip, in the order the strips are declared
    rows: dict[str, list[int]] = {}
    for i, (strip, _, _) in enumerate(cells):
        rows.setdefault(strip, []).append(i)
    row_w = {k: sum(cells[i][1].get_width() + PAD for i in v) + PAD for k, v in rows.items()}
    row_h = {k: max(cells[i][1].get_height() for i in v) + 2 * PAD for k, v in rows.items()}
    atlas_surf = pygame.Surface((max(row_w.values()), sum(row_h.values())), pygame.SRCALPHA)
    frames, strips, y = [], {}, 0
    for strip, idxs in rows.items():
        x = PAD
        strips[strip] = [len(frames), len(frames) + len(idxs)]
        for i in idxs:
            _, cell, ax = cells[i]
            atlas_surf.blit(cell, (x, y + PAD))
            frames.append({"x": x, "y": y + PAD, "w": cell.get_width(), "h": cell.get_height(), "ax": ax, "fy": cell.get_height()})
            x += cell.get_width() + PAD
        y += row_h[strip]
    pygame.image.save(atlas_surf, str(atlas_path))

    data = json.loads(def_path.read_text(encoding="utf-8")) if def_path.exists() else {}
    data["frames"], data["strips"] = frames, strips
    def_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{name}: wrote {atlas_path.relative_to(ROOT)} {atlas_surf.get_size()} and {len(frames)} frames "
          f"to {def_path.relative_to(ROOT)}")


def main(argv: list[str]) -> None:
    wanted = argv or ["all"]
    names = list(CHARACTERS) if "all" in wanted else wanted
    unknown = [n for n in names if n not in CHARACTERS]
    if unknown:
        raise SystemExit(f"unknown character(s): {', '.join(unknown)} (choose from {', '.join(CHARACTERS)})")
    for name in names:
        build(name, CHARACTERS[name])


if __name__ == "__main__":
    main(sys.argv[1:])
