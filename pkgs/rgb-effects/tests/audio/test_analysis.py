import numpy as np
import pytest

from rgb_effects.audio.analysis import SAMPLE_RATE, Analyzer, band_edges, dbfs


def _tone(frequency: float, amplitude: float, frames: int = 4096) -> np.ndarray:
    times = np.arange(frames) / SAMPLE_RATE
    mono = (amplitude * np.sin(2 * np.pi * frequency * times)).astype(np.float32)
    return np.stack([mono, mono], axis=1)


def test_dbfs_of_full_scale_square_is_zero() -> None:
    assert dbfs(np.ones(256, dtype=np.float32)) == pytest.approx(0.0, abs=1e-6)


def test_band_edges_are_increasing() -> None:
    edges = band_edges(21)
    assert len(edges) == 22 and bool(np.all(np.diff(edges) > 0))


def test_tone_lights_its_band_most() -> None:
    bands = Analyzer(21).process(_tone(1000.0, 0.5)).bands
    edges = band_edges(21) * SAMPLE_RATE / 4096
    expected = int(np.searchsorted(edges, 1000.0)) - 1
    assert int(np.argmax(bands)) == expected


def test_silence_is_not_loud() -> None:
    features = Analyzer(21).process(np.zeros((1024, 2), dtype=np.float32))
    assert not features.loud


def test_tone_is_loud() -> None:
    assert Analyzer(21).process(_tone(440.0, 0.1, 1024)).loud


def test_quiet_right_channel_reads_lower() -> None:
    block = _tone(440.0, 0.5, 1024)
    block[:, 1] *= 0.1
    features = Analyzer(21).process(block)
    assert features.right_dbfs < features.left_dbfs


@pytest.mark.parametrize("block", [np.zeros((0, 2)), np.zeros((16, 1)), np.zeros(16)])
def test_process_rejects_malformed_block(block: np.ndarray) -> None:
    with pytest.raises(ValueError):
        Analyzer(21).process(block.astype(np.float32))


def test_silence_after_sound_reads_as_empty_bands() -> None:
    analyzer = Analyzer(21)
    analyzer.process(_tone(1000.0, 0.5))
    bands = analyzer.process(np.zeros((4096, 2), dtype=np.float32)).bands
    assert float(bands.max()) == 0.0


def test_silence_from_the_start_reads_as_empty_bands() -> None:
    bands = Analyzer(21).process(np.zeros((1024, 2), dtype=np.float32)).bands
    assert float(bands.max()) == 0.0


def test_chroma_of_a_440_is_pitch_class_a() -> None:
    chroma = Analyzer(21).process(_tone(440.0, 0.5)).chroma
    assert chroma is not None and int(np.argmax(chroma)) == 9


def test_chroma_sums_to_one() -> None:
    chroma = Analyzer(21).process(_tone(261.6, 0.5)).chroma
    assert chroma is not None and float(chroma.sum()) == pytest.approx(1.0)


def test_steady_tone_has_no_onset_after_settling() -> None:
    analyzer = Analyzer(21)
    onsets = [analyzer.process(_tone(440.0, 0.3, 1024)).onset for _ in range(80)]
    assert max(onsets[60:]) == 0.0


def test_burst_after_quiet_is_an_onset() -> None:
    analyzer = Analyzer(21)
    rng = np.random.default_rng(1)
    for _ in range(60):
        analyzer.process((rng.standard_normal((1024, 2)) * 0.002).astype(np.float32))
    burst = (rng.standard_normal((1024, 2)) * 0.5).astype(np.float32)
    assert analyzer.process(burst).onset > 0


def test_silence_has_no_onset() -> None:
    analyzer = Analyzer(21)
    assert analyzer.process(np.zeros((1024, 2), dtype=np.float32)).onset == 0.0
