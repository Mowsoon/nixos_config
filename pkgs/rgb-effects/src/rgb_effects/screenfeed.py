import asyncio
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

WIDTH = 64
HEIGHT = 36
FRAME_BYTES = WIDTH * HEIGHT * 3


@dataclass(frozen=True, slots=True)
class FeedSettings:
    launcher: str
    plugin_path: str
    fps: int


class FrameListener(Protocol):
    def screen_frame(self, frame: NDArray[np.uint8]) -> None: ...


def feed_command(settings: FeedSettings, descriptor: int, node: int) -> Sequence[str]:
    return (
        settings.launcher,
        "-q",
        "pipewiresrc",
        f"fd={descriptor}",
        f"path={node}",
        "do-timestamp=true",
        "!",
        f"video/x-raw,max-framerate={settings.fps}/1",
        "!",
        "videoconvert",
        "!",
        "videoscale",
        "!",
        f"video/x-raw,format=RGB,width={WIDTH},height={HEIGHT}",
        "!",
        "fdsink",
        "fd=1",
    )


class ScreenFeed:
    def __init__(self, settings: FeedSettings, listener: FrameListener) -> None:
        self._settings = settings
        self._listener = listener

    async def run(self, descriptor: int, node: int) -> None:
        environment = dict(os.environ, GST_PLUGIN_SYSTEM_PATH_1_0=self._settings.plugin_path)
        try:
            process = await asyncio.create_subprocess_exec(
                *feed_command(self._settings, descriptor, node),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                pass_fds=(descriptor,),
                env=environment,
            )
        finally:
            os.close(descriptor)
        try:
            await self._read(process)
        finally:
            if process.returncode is None:
                process.terminate()
            await process.wait()

    async def _read(self, process: asyncio.subprocess.Process) -> None:
        stream = process.stdout
        if stream is None:
            return
        while True:
            try:
                data = await stream.readexactly(FRAME_BYTES)
            except asyncio.IncompleteReadError:
                logger.info("screen feed ended")
                return
            frame = np.frombuffer(data, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3)
            self._listener.screen_frame(frame)
