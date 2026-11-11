"""Game: fixed-timestep loop (60 updates/s), world update order and render hand-off."""
from __future__ import annotations

import time
from pathlib import Path

import pygame

from src.config.settings import (LOGICAL_HEIGHT, LOGICAL_WIDTH, MAX_CATCHUP_STEPS, UPDATES_PER_SECOND,
                                 CharacterConfig, KeyScheme, Stage, load_character_config)
from src.engine.input import Commands, InputMapper
from src.engine.physics import resolve_hits
from src.engine.renderer import Renderer
from src.entities.fighter import Fighter
from src.entities.projectile import Projectile
from src.utils.spritesheet import SpriteSheet

STEP = 1.0 / UPDATES_PER_SECOND


class FixedTimestep:
    """Accumulator that converts elapsed real time into a capped number of simulation steps."""

    def __init__(self, step: float = STEP, max_steps: int = MAX_CATCHUP_STEPS) -> None:
        self.step = step
        self.max_steps = max_steps
        self.accumulator = 0.0

    def advance(self, elapsed: float) -> int:
        self.accumulator += elapsed
        steps = 0
        while self.accumulator >= self.step - 1e-9 and steps < self.max_steps:
            self.accumulator -= self.step
            steps += 1
        if self.accumulator >= self.step - 1e-9:  # fell behind: drop the excess (no spiral of death)
            self.accumulator = 0.0
        return max(steps, 0)


class Game:
    def __init__(self, headless: bool = False, config: CharacterConfig | None = None) -> None:
        pygame.init()
        self.headless = headless
        self.config = config or load_character_config()
        self.stage = Stage()
        self.keys = KeyScheme()
        if headless:
            self.screen = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
        else:
            self.screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT))
            pygame.display.set_caption("Street Fighter - Versión Políticos")
        sheet = SpriteSheet.load(self.config.sheet_path, self.config.frames,
                                 self.config.background_tolerance, self.config.sprite_scale,
                                 extras={"projectile": self.config.projectile_sprite})
        self.renderer = Renderer(self.screen, sheet, self.config.background_path)
        self.fighters: list[Fighter] = [
            Fighter(0, 300, self.config, self.stage, facing=1),
            Fighter(1, 724, self.config, self.stage, facing=-1),
        ]
        self.projectiles: list[Projectile] = []
        self.debug_overlay = False
        self.running = True

    # ---- one simulation step (no wall-clock access) ---------------------------------------
    def update(self, commands_p1: Commands, commands_p2: Commands) -> None:
        spawned: list[Projectile] = []
        for fighter, other, cmd in ((self.fighters[0], self.fighters[1], commands_p1),
                                    (self.fighters[1], self.fighters[0], commands_p2)):
            spawned += fighter.update(cmd, other, self.stage, self._owns_projectile(fighter.id))
        self.projectiles.extend(spawned)
        for projectile in self.projectiles:
            projectile.update(self.stage)

        hitboxes = [f.active_hitbox for f in self.fighters if f.active_hitbox is not None]
        hitboxes += [p.hitbox for p in self.projectiles if p.alive]
        by_id = {f.id: f for f in self.fighters}
        events = resolve_hits(hitboxes, [f.hurtbox for f in self.fighters],
                              lambda defender_id, hit: by_id[defender_id].is_blocking(hit))
        for event in events:
            by_id[event.defender_id].apply_hit(event)
            for projectile in self.projectiles:
                if projectile.hitbox is event.hitbox:
                    projectile.kill()
        self.projectiles = [p for p in self.projectiles if p.alive]

    def _owns_projectile(self, fighter_id: int) -> bool:
        return any(p.owner_id == fighter_id and p.alive for p in self.projectiles)

    # ---- real-time loop ---------------------------------------------------------------------
    def run(self) -> None:
        clock = pygame.time.Clock()
        timestep = FixedTimestep()
        last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            elapsed, last = now - last, now
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == self.keys.debug_toggle:
                    self.debug_overlay = not self.debug_overlay
            for _ in range(timestep.advance(elapsed)):
                pressed = pygame.key.get_pressed()
                self.update(InputMapper.read(pressed, self.keys), InputMapper.read_training(pressed, self.keys))
            self.renderer.draw(self)
            pygame.display.flip()
            clock.tick(UPDATES_PER_SECOND)
        pygame.quit()
