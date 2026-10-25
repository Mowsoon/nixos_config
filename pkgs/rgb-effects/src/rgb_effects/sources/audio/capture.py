import asyncio
import logging
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from rgb_effects.retry import RetryPolicy, Sleep
from rgb_effects.sources.audio.analysis import Analyzer, Features

logger = logging.getLogger(__name__)

CHANNELS = 2
BLOCK_FRAMES = 1024
BYTES_PER_SAMPLE = 4
BLOCK_BYTES = BLOCK_FRAMES * CHANNELS * BYTES_PER_SAMPLE
STREAM_PROPERTIES = (
    "{ stream.capture.sink=true node.dont-move=true node.name=rgb-effects-monitor"
    ' node.description="RGB effects monitor" }'
)


class AudioListener(Protocol):
    def audio_features(self, features: Features) -> None: ...


def recorder_command(recorder: str) -> Sequence[str]:
    return (
        recorder,
        "--raw",
        "--rate",
        "48000",
        "--channels",
        str(CHANNELS),
        "--format",
        "f32",
        "--latency",
        str(BLOCK_FRAMES),
        "-P",
        STREAM_PROPERTIES,
        "-",
    )


class AudioCapture:
    def __init__(
        self,
        recorder: str,
        analyzer: Analyzer,
        listener: AudioListener,
        retry: RetryPolicy,
        sleep: Sleep,
    ) -> None:
        self._command = recorder_command(recorder)
        self._analyzer = analyzer
        self._listener = listener
        self._retry = retry
        self._sleep = sleep

    async def run(self) -> None:
        delay = self._retry.initial_seconds
        while True:
            try:
                await self._record()
                delay = self._retry.initial_seconds
            except OSError as err:
                logger.warning("audio capture: %s, retrying in %.0f s", err, delay)
            await self._sleep(self._retry.jittered(delay))
            delay = self._retry.next_delay(delay)

    async def _record(self) -> None:
        process = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await self._read(process)
        finally:
            if process.returncode is None:
                process.terminate()
            await process.wait()
        logger.info("audio capture ended with status %s", process.returncode)

    async def _read(self, process: asyncio.subprocess.Process) -> None:
        stream = process.stdout
        if stream is None:
            return
        logger.info("audio capture started")
        while True:
            try:
                data = await stream.readexactly(BLOCK_BYTES)
            except asyncio.IncompleteReadError:
                return
            block = np.frombuffer(data, dtype=np.float32).reshape(-1, CHANNELS)
            self._listener.audio_features(self._analyzer.process(block))
