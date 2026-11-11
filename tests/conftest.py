import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from src.config.settings import FrameRect, Stage, load_character_config
from src.engine.game import Game
from src.engine.input import Commands
from src.entities.fighter import Fighter


@pytest.fixture(scope="session", autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def test_sheet(tmp_path):
    """Gray sheet with nine coloured 20x30 blocks; returns (path, frame rects)."""
    surf = pygame.Surface((300, 100))
    surf.fill((128, 128, 128))
    rects = []
    for i in range(9):
        x, y = 10 + (i % 5) * 55, 10 + (i // 5) * 45
        pygame.draw.rect(surf, (10 + i * 20, 200 - i * 10, 30), (x, y, 20, 30))
        rects.append(FrameRect(x, y, 20, 30, 10, 30))
    path = tmp_path / "sheet.png"
    pygame.image.save(surf, str(path))
    return path, rects


@pytest.fixture(scope="session")
def config():
    return load_character_config()


@pytest.fixture
def stage():
    return Stage()


@pytest.fixture
def pair(config, stage):
    """Player at x=300 facing right and dummy at x=724 facing left."""
    return Fighter(0, 300, config, stage, 1), Fighter(1, 724, config, stage, -1)


@pytest.fixture
def close_pair(config, stage):
    """Fighters 120px apart: inside punch range (reach ~100 + half hurtbox 40)."""
    return Fighter(0, 400, config, stage, 1), Fighter(1, 520, config, stage, -1)


@pytest.fixture
def game():
    return Game(headless=True)


NONE = Commands()


def run(fighter, other, cmd, n=1, has_projectile=False):
    spawned = []
    for _ in range(n):
        spawned += fighter.update(cmd, other, fighter.stage, has_projectile)
    return spawned
