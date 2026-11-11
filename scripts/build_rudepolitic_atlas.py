"""Slice assets/rudepolitic.png into a clean, transparent atlas for the "Rude Politic" fighter.

Usage: python scripts/build_rudepolitic_atlas.py

Input : assets/rudepolitic.png  (1536x1024, flat gray background, 5 labelled animation strips)
Output: assets/characters/rudepolitic.png   RGBA atlas, one pose per cell, no gray, no labels, no bleed
        assets/characters/rudepolitic.json  its "frames" and "strips" keys are (re)written; every other
                                            key (animations, attacks, ...) is kept as authored.

Each strip is a hand-chosen window that excludes its label and the neighbouring strips. Inside a window
the poses are the connected foreground components; poses that touch are cut at their emptiest column.
A pose is cut out by its OWN pixels (not by its bounding rectangle), so overlapping rectangles
(jump frames 4/5, punch frames 2/3) cannot leak into each other. `ax` is the median x of the hips/thighs (the planted part, so the body
doesn't slide between poses) and `fy` the bottom of the pose (the floor line).
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "rudepolitic.png"
OUT_PNG = ROOT / "assets" / "characters" / "rudepolitic.png"
OUT_JSON = ROOT / "assets" / "characters" / "rudepolitic.json"

TOL = 28            # distance from the sheet's gray that still counts as background
MIN_AREA = 150      # components smaller than this are "specks" (sparks, a fingertip): attached to the nearest pose
HOLE_MAX = 250      # enclosed background-coloured pockets up to this many px are suit highlights (kept opaque)
SPECK_MIN = 12      # ...unless they are tiny noise
PAD = 2             # transparent margin between atlas cells
# strip name: (x0, x1, y0, y1, expected pose count)
STRIPS = {
    "walk":    (0, 1536, 55, 330, 6),
    "punch":   (0, 805, 380, 640, 5),
    "kick":    (810, 1536, 380, 640, 5),
    "jump":    (0, 810, 640, 1000, 5),
    "special": (810, 1536, 695, 1000, 5),
}
# (x, y, w, h) of the dark text labels, blanked out before measuring
LABELS = [(14, 16, 205, 35), (14, 338, 165, 34), (833, 338, 118, 34), (14, 656, 104, 44), (814, 656, 415, 44)]


def pose_masks(fg: pygame.mask.Mask, win: pygame.Rect, n: int) -> list[pygame.mask.Mask]:
    """Return `n` full-sheet-sized masks, one per pose of the strip window, left to right."""
    region = pygame.mask.Mask(fg.get_size())
    for y in range(win.y, win.bottom):                      # intersect fg with the window
        for x in range(win.x, win.right):
            if fg.get_at((x, y)):
                region.set_at((x, y), 1)
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


def main() -> None:
    sheet = pygame.image.load(str(SRC))
    rgba = pygame.Surface(sheet.get_size(), pygame.SRCALPHA)   # same pixel format as the RGBA mask surface
    rgba.blit(sheet, (0, 0))
    bg = sheet.get_at((0, 0))
    bgm = pygame.mask.from_threshold(sheet, bg, (TOL, TOL, TOL, 255))
    w, h = sheet.get_size()
    fg = pygame.mask.Mask((w, h), fill=True)
    for comp in bgm.connected_components():                 # background = gray regions touching the sheet edge;
        r = comp.get_bounding_rects()[0]                    # small gray-ish pixels enclosed by the suit stay opaque;
        if r.x == 0 or r.y == 0 or r.right == w or r.bottom == h or comp.count() > HOLE_MAX:   # big enclosed pockets
            fg.erase(comp, (0, 0))                          # (between the legs, around dust) are background too
    for lx, ly, lw, lh in LABELS:
        fg.erase(pygame.mask.Mask((lw, lh), fill=True), (lx, ly))

    cells: list[tuple[str, pygame.Surface, int]] = []       # (strip, RGBA cell, head-centre x within cell)
    for name, (x0, x1, y0, y1, n) in STRIPS.items():
        for m in pose_masks(fg, pygame.Rect(x0, y0, x1 - x0, y1 - y0), n):
            box = m.get_bounding_rects()
            r = box[0].unionall(box[1:])
            cell = m.to_surface(setsurface=rgba, unsetcolor=(0, 0, 0, 0)).subsurface(r).copy()
            band = range(r.y + r.h // 2, r.y + r.h * 9 // 10)      # hips / thighs: the part that stays planted
            xs = sorted(x - r.x for y in band for x in range(r.x, r.right)
                        if m.get_at((x, y)) and sum(sheet.get_at((x, y))[:3]) < 330)   # dark suit pixels only
            ax = xs[len(xs) // 2] if xs else r.w // 2
            cells.append((name, cell, ax))

    # pack: one row per strip
    rows: dict[str, list[int]] = {}
    for i, (name, _, _) in enumerate(cells):
        rows.setdefault(name, []).append(i)
    row_w = {k: sum(cells[i][1].get_width() + PAD for i in v) + PAD for k, v in rows.items()}
    row_h = {k: max(cells[i][1].get_height() for i in v) + 2 * PAD for k, v in rows.items()}
    atlas = pygame.Surface((max(row_w.values()), sum(row_h.values())), pygame.SRCALPHA)
    frames, strips, y = [], {}, 0
    for name, idxs in rows.items():
        x = PAD
        strips[name] = [len(frames), len(frames) + len(idxs)]
        for i in idxs:
            _, cell, ax = cells[i]
            atlas.blit(cell, (x, y + PAD))
            frames.append({"x": x, "y": y + PAD, "w": cell.get_width(), "h": cell.get_height(), "ax": ax, "fy": cell.get_height()})
            x += cell.get_width() + PAD
        y += row_h[name]
    pygame.image.save(atlas, str(OUT_PNG))

    data = json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else {}
    data["frames"], data["strips"] = frames, strips
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_PNG.relative_to(ROOT)} {atlas.get_size()} and {len(frames)} frames to {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
