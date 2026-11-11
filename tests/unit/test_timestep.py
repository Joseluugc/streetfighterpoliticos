import inspect

from src.engine.game import Game, FixedTimestep


def test_n_steps_for_n_sixtieths():
    ts = FixedTimestep()
    assert sum(ts.advance(1 / 60) for _ in range(60)) == 60


def test_catchup_capped_and_excess_dropped():
    ts = FixedTimestep()
    assert ts.advance(1.0) == 5
    assert ts.advance(0.0) == 0


def test_partial_time_accumulates():
    ts = FixedTimestep()
    assert ts.advance(0.01) == 0
    assert ts.advance(0.01) == 1


def test_update_takes_no_time_argument():
    params = list(inspect.signature(Game.update).parameters)
    assert params == ["self", "commands_p1", "commands_p2"]
