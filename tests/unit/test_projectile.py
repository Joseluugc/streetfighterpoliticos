from src.config.settings import Stage
from src.entities.projectile import Projectile


def test_moves_forward_each_update(config):
    p = Projectile(0, 100, 300, 1, config.special.projectile)
    p.update(Stage())
    assert p.x == 100 + config.special.projectile.speed
    q = Projectile(0, 500, 300, -1, config.special.projectile)
    q.update(Stage())
    assert q.x == 500 - config.special.projectile.speed


def test_lifetime_expires_after_90_updates(config):
    p = Projectile(0, 0, 300, 1, config.special.projectile)
    stage = Stage(left=-10_000, right=10_000)
    for _ in range(89):
        p.update(stage)
    assert p.alive
    p.update(stage)
    assert not p.alive


def test_dies_when_leaving_stage(config):
    p = Projectile(0, 1000, 300, 1, config.special.projectile)
    for _ in range(10):
        p.update(Stage())
    assert not p.alive


def test_own_box_follows_position_and_kill(config):
    p = Projectile(0, 100, 300, 1, config.special.projectile)
    p.update(Stage())
    assert p.hitbox.rect.center == (round(p.x), 300)
    assert p.hitbox.damage == 10 and p.hitbox.owner_id == 0
    p.kill()
    assert not p.alive
