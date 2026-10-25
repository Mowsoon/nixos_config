import asyncio
from pathlib import Path

import pytest

from rgb_effects.audio.analysis import Analyzer, Features
from rgb_effects.audio.capture import BLOCK_BYTES, AudioCapture, recorder_command
from rgb_effects.retry import RetryPolicy


class StopCapture(Exception):
    pass


class Recorder:
    def __init__(self) -> None:
        self.features: list[Features] = []

    def audio_features(self, features: Features) -> None:
        self.features.append(features)


async def _stop(seconds: float) -> None:
    raise StopCapture


def test_command_captures_the_sink_monitor_without_moving() -> None:
    properties = recorder_command("/bin/pw-record")[-2]
    assert "stream.capture.sink=true" in properties and "node.dont-move=true" in properties


def test_command_writes_raw_float_stereo_to_stdout() -> None:
    command = recorder_command("/bin/pw-record")
    assert command[0] == "/bin/pw-record" and command[-1] == "-"
    assert "--raw" in command and "f32" in command


async def test_capture_feeds_every_complete_block(tmp_path: Path) -> None:
    script = tmp_path / "recorder"
    script.write_text(f"#!/bin/sh\nhead -c {BLOCK_BYTES * 3} /dev/zero\n", encoding="utf-8")
    script.chmod(0o700)
    recorder = Recorder()
    capture = AudioCapture(str(script), Analyzer(21), recorder, RetryPolicy(1.0, 2.0), _stop)
    with pytest.raises(StopCapture):
        await asyncio.wait_for(capture.run(), 10)
    assert len(recorder.features) == 3


async def test_missing_recorder_is_retried(tmp_path: Path) -> None:
    recorder = Recorder()
    capture = AudioCapture(
        str(tmp_path / "absent"), Analyzer(21), recorder, RetryPolicy(1.0, 2.0), _stop
    )
    with pytest.raises(StopCapture):
        await capture.run()
    assert recorder.features == []
