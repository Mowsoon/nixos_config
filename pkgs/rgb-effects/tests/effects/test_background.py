import numpy as np

from rgb_effects.color import Color
from rgb_effects.effects.background import ON, Automaton, Background, BackgroundSettings
from rgb_effects.render.palette import PaletteInputs, build_palette

SHAPE = (6, 21)
PALETTE = build_palette(PaletteInputs(Color(255, 255, 255), 1.0, 0.6, Color(0, 0, 255), None), 8)


def _background() -> Background:
    return Background(SHAPE, BackgroundSettings(idle_seconds=30.0), 7)


def test_values_stay_in_unit_range() -> None:
    values = _background().values()
    assert values.shape == SHAPE and float(values.min()) >= 0 and float(values.max()) <= 1


def test_flow_moves_over_time() -> None:
    background = _background()
    background.advance(0.0, 0.0, 0.0)
    before = background.values()
    background.advance(5.0, 0.0, 0.0)
    assert not np.allclose(before, background.values())


def test_activity_speeds_up_the_flow() -> None:
    calm, busy = _background(), _background()
    for background, rate in ((calm, 0.0), (busy, 4.0)):
        background.advance(0.0, rate, 0.0)
        background.advance(1.0, rate, 0.0)
    reference = _background()
    reference.advance(0.0, 0.0, 0.0)
    calm_change = np.abs(calm.values() - reference.values()).sum()
    busy_change = np.abs(busy.values() - reference.values()).sum()
    assert busy_change > calm_change


def test_idle_fades_in_the_automaton() -> None:
    background = _background()
    background.advance(0.0, 0.0, 40.0)
    background.advance(3.0, 0.0, 43.0)
    assert background.mix == 1.0


def test_activity_fades_out_the_automaton() -> None:
    background = _background()
    background.advance(0.0, 0.0, 40.0)
    background.advance(3.0, 0.0, 43.0)
    background.advance(3.5, 1.0, 0.0)
    assert background.mix == 0.0


def test_field_has_one_color_per_cell() -> None:
    assert _background().field(PALETTE).shape == (*SHAPE, 3)


def test_brians_brain_on_cell_dies_next_step() -> None:
    automaton = Automaton((5, 5))
    automaton.cells[2, 2] = ON
    automaton.step()
    assert automaton.cells[2, 2] == 2


def test_brians_brain_cell_with_two_on_neighbours_is_born() -> None:
    automaton = Automaton((5, 5))
    automaton.cells[1, 1] = ON
    automaton.cells[1, 3] = ON
    automaton.step()
    assert automaton.cells[1, 2] == ON
