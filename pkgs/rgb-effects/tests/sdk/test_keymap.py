from evdev import ecodes

from rgb_effects.sdk.keymap import AZERTY_LED_CODES, led_index_by_code


def test_physical_q_position_is_azerty_a() -> None:
    assert led_index_by_code(["Key: Escape", "Key: A"])[ecodes.KEY_Q] == 1


def test_unknown_led_names_are_skipped() -> None:
    assert dict(led_index_by_code(["Logo", "Key: Space"])) == {ecodes.KEY_SPACE: 1}


def test_every_code_maps_to_a_single_led() -> None:
    codes = list(AZERTY_LED_CODES.values())
    assert len(codes) == len(set(codes))
