"""Crop a character sheet PNG into 9 cached surfaces (plus mirrored copies)."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pygame

from src.config.settings import FrameRect

FRAME_COUNT = 9


class SpriteSheetError(Exception):
    """Raised when a sheet is missing or malformed. The message always names the file."""


def _remove_background(image: pygame.Surface, tolerance: int) -> pygame.Surface:
    """Return an RGBA copy where pixels close to the top-left pixel colour are transparent."""
    bg = image.get_at((0, 0))
    bg_mask = pygame.mask.from_threshold(image, bg, (tolerance, tolerance, tolerance, 255))
    bg_mask.invert()  # now set pixels = foreground
    return bg_mask.to_surface(setsurface=_to_rgba(image), unsetcolor=(0, 0, 0, 0))


class SpriteSheet:
    """Holds exactly 9 frames, sliced once at load time. Never touches files after `load`."""

    def __init__(self, right: list[pygame.Surface], left: list[pygame.Surface],
                 anchors: list[tuple[int, int]], extras: dict[str, tuple[pygame.Surface, pygame.Surface]]):
        self._right = right
        self._left = left
        self._anchors = anchors
        self._extras = extras
        self.frame_count = len(right)

    @classmethod
    def load(cls, path: str | Path, frames: Sequence[FrameRect], background_tolerance: int = 0,
             scale: float = 1.0, extras: dict[str, tuple[int, int, int, int]] | None = None) -> "SpriteSheet":
        path = Path(path)
        if len(frames) != FRAME_COUNT:
            raise SpriteSheetError(f"{path}: expected exactly {FRAME_COUNT} frames, got {len(frames)}")
        try:
            image = pygame.image.load(str(path))
        except (FileNotFoundError, pygame.error) as exc:
            raise SpriteSheetError(f"Cannot load spritesheet {path}: {exc}") from exc
        width, height = image.get_size()
        sheet_rect = pygame.Rect(0, 0, width, height)
        rects = [(f"frame {i + 1}", pygame.Rect(f.x, f.y, f.w, f.h)) for i, f in enumerate(frames)]
        for name, (ex, ey, ew, eh) in (extras or {}).items():
            rects.append((name, pygame.Rect(ex, ey, ew, eh)))
        for name, rect in rects:
            if rect.w <= 0 or rect.h <= 0 or not sheet_rect.contains(rect):
                raise SpriteSheetError(
                    f"{path}: {name} rect {tuple(rect)} is outside the {width}x{height} image")
        keyed = _remove_background(image, background_tolerance) if background_tolerance else _to_rgba(image)

        def cut(rect: pygame.Rect) -> pygame.Surface:
            surf = keyed.subsurface(rect).copy()
            if scale != 1.0:
                surf = pygame.transform.smoothscale(
                    surf, (max(1, round(rect.w * scale)), max(1, round(rect.h * scale))))
            return surf

        right: list[pygame.Surface] = []
        left: list[pygame.Surface] = []
        anchors: list[tuple[int, int]] = []
        for f in frames:
            surf = cut(pygame.Rect(f.x, f.y, f.w, f.h))
            right.append(surf)
            left.append(pygame.transform.flip(surf, True, False))
            anchors.append((round(f.anchor_x * scale), round(f.foot_y * scale)))
        extra_surfaces = {}
        for name, (ex, ey, ew, eh) in (extras or {}).items():
            surf = cut(pygame.Rect(ex, ey, ew, eh))
            extra_surfaces[name] = (surf, pygame.transform.flip(surf, True, False))
        return cls(right, left, anchors, extra_surfaces)

    def frame(self, index: int, facing: int = 1) -> pygame.Surface:
        return (self._right if facing >= 0 else self._left)[index]

    def anchor(self, index: int, facing: int = 1) -> tuple[int, int]:
        """Offset from the surface's top-left to the fighter's feet-centre point."""
        ax, foot = self._anchors[index]
        if facing < 0:
            ax = self._right[index].get_width() - ax
        return ax, foot

    def extra(self, name: str, facing: int = 1) -> pygame.Surface:
        right, left = self._extras[name]
        return right if facing >= 0 else left


def _to_rgba(image: pygame.Surface) -> pygame.Surface:
    out = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    out.blit(image, (0, 0))
    return out
