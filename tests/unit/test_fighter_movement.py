from src.engine.input import Commands
from src.entities.states import FighterState as S
from tests.conftest import NONE, run


def test_walk_right_constant_speed_and_frame(pair, config):
    p, d = pair
    x0 = p.x
    run(p, d, Commands(right=True), 10)
    assert p.x == x0 + 10 * config.walk_speed
    assert p.state is S.WALKING and p.frame_index == 2


def test_release_returns_to_idle(pair):
    p, d = pair
    run(p, d, Commands(right=True), 3)
    run(p, d, NONE)
    assert p.state is S.IDLE


def test_stage_bounds(pair, stage):
    p, d = pair
    run(p, d, Commands(left=True), 400)
    assert p.x >= stage.left + p.config.hurtbox.w / 2 - 1e-6
    p2, d2 = d, p
    run(p2, d2, Commands(right=True), 400)
    assert p2.x <= stage.right - p2.config.hurtbox.w / 2 + 1e-6


def test_left_and_right_together_stay_idle(pair):
    p, d = pair
    x0 = p.x
    run(p, d, Commands(left=True, right=True), 5)
    assert p.state is S.IDLE and p.x == x0


def test_jump_arc_frames_and_landing(pair, config, stage):
    p, d = pair
    run(p, d, Commands(jump=True))
    assert p.state is S.JUMPING and p.frame_index == 3 and p.vy == config.jump_velocity
    seen_fall = False
    for _ in range(100):
        run(p, d, NONE)
        if p.state is S.FALLING:
            seen_fall = True
            assert p.frame_index == 4
        if p.state is S.IDLE:
            break
    assert seen_fall and p.state is S.IDLE and p.y == stage.floor_y


def test_no_double_jump(pair):
    p, d = pair
    run(p, d, Commands(jump=True))
    run(p, d, Commands(jump=True), 5)
    assert p.state in (S.JUMPING, S.FALLING)
    assert p.y < p.stage.floor_y


def test_air_direction_locked_at_takeoff(pair, config):
    p, d = pair
    run(p, d, Commands(jump=True, right=True))
    x0 = p.x
    run(p, d, Commands(left=True), 5)
    assert p.x > x0


def test_landing_with_direction_held_walks(pair):
    p, d = pair
    run(p, d, Commands(jump=True))
    for _ in range(100):
        run(p, d, Commands(right=True) if p.state is S.FALLING else NONE)
        if p.grounded:
            break
    assert p.state is S.WALKING


def test_attacks_ignored_in_air(pair):
    p, d = pair
    run(p, d, Commands(jump=True))
    run(p, d, Commands(punch=True, kick=True, special=True, guard=True), 3)
    assert p.state in (S.JUMPING, S.FALLING)


def test_fighters_cannot_overlap_on_ground(close_pair):
    p, d = close_pair
    for _ in range(200):
        run(p, d, Commands(right=True))
    assert abs(p.x - d.x) >= p.config.hurtbox.w - 1e-6
    assert p.x < d.x


def test_auto_face_opponent(pair):
    p, d = pair
    d.x = 100
    run(p, d, NONE)
    assert p.facing == -1
