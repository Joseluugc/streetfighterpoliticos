from src.engine.input import Commands
from src.engine.physics import Hitbox, HitEvent
from src.entities.states import FighterState as S
from tests.conftest import NONE, run

import pygame


def count_active(fighter, other, cmd, total):
    frames = 0
    states = []
    for i in range(total):
        run(fighter, other, cmd if i == 0 else NONE)
        states.append(fighter.state)
        frames += fighter.active_hitbox is not None
    return frames, states


def test_punch_phases(pair):
    p, d = pair
    active, states = count_active(p, d, Commands(punch=True), 4)
    assert p.state is S.PUNCHING and p.frame_index == 5
    # update 1 enters the state; startup is 4 updates, active 3, recovery 8 (15 total)
    active, _ = count_active(p, d, NONE, 14)
    assert active == 3
    assert p.state is S.IDLE


def test_kick_longer_and_stronger(pair, config):
    p, d = pair
    run(p, d, Commands(kick=True))
    assert p.state is S.KICKING and p.frame_index == 6
    active, _ = count_active(p, d, NONE, config.kick.total)
    assert active == config.kick.active and p.state is S.IDLE
    assert config.kick.damage > config.punch.damage and config.kick.total > config.punch.total


def test_actions_locked_until_recovery_ends(pair):
    p, d = pair
    run(p, d, Commands(punch=True))
    run(p, d, Commands(right=True, jump=True, kick=True), 3)
    assert p.state is S.PUNCHING


def test_guard_held_and_released(pair):
    p, d = pair
    x0 = p.x
    run(p, d, Commands(guard=True), 5)
    assert p.state is S.DEFENDING and p.frame_index == 7 and p.x == x0
    run(p, d, NONE)
    assert p.state is S.IDLE


def hit(attacker_x, damage=5, knockback=16):
    return HitEvent(0, 1, Hitbox(pygame.Rect(attacker_x, 400, 10, 10), 0, damage, knockback, 15, 8), False)


def test_hit_applies_damage_hitstun_and_interrupts(pair):
    p, d = pair
    run(d, p, Commands(punch=True))
    d.apply_hit(hit(100))
    assert d.health == 95 and d.state is S.HIT_STUN
    assert d.active_hitbox is None
    run(d, p, NONE, 15)
    assert d.state is S.IDLE


def test_block_from_front_no_damage(pair):
    p, d = pair
    run(d, p, Commands(guard=True))
    box = Hitbox(pygame.Rect(d.x - 60, 400, 10, 10), 0, 5, 16, 15, 8)  # attacker on the left = d's facing side
    assert d.is_blocking(box)
    d.apply_hit(HitEvent(0, 1, box, True))
    assert d.health == 100 and d.state is S.DEFENDING


def test_block_fails_from_behind(pair):
    p, d = pair
    run(d, p, Commands(guard=True))
    box = Hitbox(pygame.Rect(d.x + 60, 400, 10, 10), 0, 5, 16, 15, 8)
    assert not d.is_blocking(box)


def test_health_clamped_at_zero(pair):
    p, d = pair
    for _ in range(30):
        d.apply_hit(hit(100, damage=8))
    assert d.health == 0


def test_special_spawns_one_projectile_at_update_12(pair, config):
    p, d = pair
    spawned = run(p, d, Commands(special=True))
    assert p.state is S.SPECIAL and p.frame_index == 8 and not spawned
    spawned = run(p, d, NONE, config.special.startup)  # released at the end of the 12th cast update
    assert len(spawned) == 1
    assert spawned[0].facing == p.facing and spawned[0].owner_id == p.id
    assert run(p, d, NONE, config.special.recovery) == []
    assert p.state is S.IDLE


def test_special_blocked_while_projectile_alive(pair):
    p, d = pair
    run(p, d, Commands(special=True), has_projectile=True)
    assert p.state is S.IDLE
