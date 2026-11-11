"""The "Ley de Vivienda" projectile: an independent entity with its own box and lifetime."""
from __future__ import annotations

import pygame

from src.config.settings import ProjectileConfig, Stage
from src.engine.physics import Hitbox


class Projectile:
    def __init__(self, owner_id: int, x: float, y: float, facing: int, config: ProjectileConfig) -> None:
        self.owner_id = owner_id
        self.x = x
        self.y = y  # centre of the projectile's box
        self.facing = 1 if facing >= 0 else -1
        self.vx = self.facing * config.speed
        self.lifetime = config.lifetime
        self.alive = True
        box = config.box
        self.hitbox = Hitbox(pygame.Rect(0, 0, box.w, box.h), owner_id, config.damage,
                             config.knockback, 0, 0)
        self._sync_box()

    def _sync_box(self) -> None:
        self.hitbox.rect.center = (round(self.x), round(self.y))

    def update(self, stage: Stage) -> None:
        if not self.alive:
            return
        self.x += self.vx
        self.lifetime -= 1
        self._sync_box()
        half = self.hitbox.rect.w / 2
        if self.lifetime <= 0 or self.x + half < stage.left or self.x - half > stage.right:
            self.kill()

    def kill(self) -> None:
        self.alive = False
