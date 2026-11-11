"""All drawing lives here. Reads game state; never mutates it."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from src.config.settings import LOGICAL_HEIGHT, LOGICAL_WIDTH
from src.utils.spritesheet import SpriteSheet

if TYPE_CHECKING:
    from src.engine.game import Game

HURTBOX_COLOR = (0, 220, 0)
HITBOX_COLOR = (230, 0, 0)
PROJECTILE_COLOR = (240, 220, 0)


class Renderer:
    def __init__(self, screen: pygame.Surface, sheet: SpriteSheet, background_path: Path | None = None) -> None:
        self.screen = screen
        self.sheet = sheet
        self.background = self._load_background(background_path)
        pygame.font.init()
        self.font = pygame.font.Font(None, 28)

    @staticmethod
    def _load_background(path: Path | None) -> pygame.Surface | None:
        if path is None or not Path(path).exists():
            return None
        image = pygame.image.load(str(path))
        if image.get_size() != (LOGICAL_WIDTH, LOGICAL_HEIGHT):
            image = pygame.transform.smoothscale(image, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
        return image.convert() if pygame.display.get_surface() else image

    def draw(self, game: "Game") -> None:
        if self.background is not None:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((40, 30, 40))
        for fighter in game.fighters:
            self._draw_fighter(fighter)
        for projectile in game.projectiles:
            self._draw_projectile(projectile)
        self._draw_hud(game)
        if game.debug_overlay:
            self._draw_debug(game)

    def _draw_fighter(self, fighter) -> None:
        idx, facing = fighter.frame_index, fighter.facing
        ax, foot = self.sheet.anchor(idx, facing)
        x, y = fighter.position
        shadow = pygame.Rect(0, 0, 90, 14)
        shadow.center = (round(x), round(y) + 2)
        shade = pygame.Surface(shadow.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shade, (0, 0, 0, 90), shade.get_rect())
        self.screen.blit(shade, shadow)
        self.screen.blit(self.sheet.frame(idx, facing), (round(x) - ax, round(y) - foot))

    def _draw_projectile(self, projectile) -> None:
        sprite = self.sheet.extra("projectile", projectile.facing)
        rect = sprite.get_rect(center=(round(projectile.x), round(projectile.y)))
        self.screen.blit(sprite, rect)

    def _draw_hud(self, game: "Game") -> None:
        labels = ("PLAYER", "DUMMY")
        for i, fighter in enumerate(game.fighters):
            w, h, margin = 380, 22, 24
            x = margin if i == 0 else LOGICAL_WIDTH - margin - w
            pygame.draw.rect(self.screen, (30, 30, 30), (x - 3, 21, w + 6, h + 6))
            pygame.draw.rect(self.screen, (120, 0, 0), (x, 24, w, h))
            fill = round(w * fighter.health / fighter.config.max_health)
            fill_x = x if i == 0 else x + w - fill
            pygame.draw.rect(self.screen, (230, 190, 30), (fill_x, 24, fill, h))
            text = self.font.render(f"{labels[i]}  {fighter.health}", True, (255, 255, 255))
            self.screen.blit(text, (x, 50) if i == 0 else (x + w - text.get_width(), 50))

    def _draw_debug(self, game: "Game") -> None:
        for fighter in game.fighters:
            pygame.draw.rect(self.screen, HURTBOX_COLOR, fighter.hurtbox.rect, 2)
            if fighter.active_hitbox is not None:
                pygame.draw.rect(self.screen, HITBOX_COLOR, fighter.active_hitbox.rect, 2)
        for projectile in game.projectiles:
            pygame.draw.rect(self.screen, PROJECTILE_COLOR, projectile.hitbox.rect, 2)
