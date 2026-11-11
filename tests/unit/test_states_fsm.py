import pytest

from src.entities.fighter import InvalidTransition
from src.entities.states import STATE_TABLE, FighterState as S


def test_required_states_exist():
    for name in ("IDLE", "WALKING", "JUMPING", "FALLING", "PUNCHING", "KICKING", "DEFENDING", "SPECIAL", "HIT_STUN"):
        assert name in S.__members__


def test_every_state_has_spec_and_frames():
    assert set(STATE_TABLE) == set(S)
    assert STATE_TABLE[S.IDLE].frames == (0, 1)
    assert [STATE_TABLE[s].frames for s in (S.WALKING, S.JUMPING, S.FALLING, S.PUNCHING, S.KICKING, S.DEFENDING, S.SPECIAL)] \
        == [(2,), (3,), (4,), (5,), (6,), (7,), (8,)]


def test_declared_transition_accepted(pair):
    p, _ = pair
    p.change_state(S.PUNCHING)
    assert p.state is S.PUNCHING


def test_undeclared_transition_rejected(pair):
    p, _ = pair
    p.change_state(S.PUNCHING)
    with pytest.raises(InvalidTransition):
        p.change_state(S.WALKING)
    assert p.state is S.PUNCHING


def test_jump_cannot_become_attack(pair):
    p, _ = pair
    p.change_state(S.JUMPING)
    with pytest.raises(InvalidTransition):
        p.change_state(S.KICKING)
