import pygame

from src.engine.input import Commands
from src.engine.physics import Hitbox, Hurtbox, place_box, resolve_hits


def hb(rect, owner=0):
    return Hitbox(pygame.Rect(rect), owner, 5, 10, 15, 8)


def test_hit_registers_on_opposing_hurtbox():
    ev = resolve_hits([hb((0, 0, 50, 50))], [Hurtbox(pygame.Rect(40, 0, 50, 50), 1)], lambda d, h: False)
    assert len(ev) == 1 and ev[0].defender_id == 1 and not ev[0].blocked


def test_no_self_hit():
    assert resolve_hits([hb((0, 0, 50, 50))], [Hurtbox(pygame.Rect(0, 0, 50, 50), 0)], lambda d, h: False) == []


def test_hit_once_per_hitbox():
    box, hurt = hb((0, 0, 50, 50)), [Hurtbox(pygame.Rect(0, 0, 50, 50), 1)]
    assert len(resolve_hits([box], hurt, lambda d, h: False)) == 1
    assert resolve_hits([box], hurt, lambda d, h: False) == []


def test_miss():
    assert resolve_hits([hb((0, 0, 10, 10))], [Hurtbox(pygame.Rect(100, 0, 10, 10), 1)], lambda d, h: False) == []


def test_blocked_flag():
    ev = resolve_hits([hb((0, 0, 50, 50))], [Hurtbox(pygame.Rect(0, 0, 50, 50), 1)], lambda d, h: True)
    assert ev[0].blocked


def test_place_box_mirrors_with_facing():
    right = place_box(100, 200, 1, 40, 20, 30, -100)
    left = place_box(100, 200, -1, 40, 20, 30, -100)
    assert right.left == 130 and left.right == 70 and right.top == left.top == 100


def test_commands_priority_and_direction_cancel():
    c = Commands(left=True, right=True, jump=True, punch=True, kick=True).resolved()
    assert not c.left and not c.right and c.kick and not c.punch and not c.jump
    assert Commands(guard=True, special=True).resolved().guard
    assert Commands(special=True, kick=True).resolved().special
    assert Commands(punch=True, jump=True).resolved().punch
    assert Commands(jump=True, right=True).resolved().right
