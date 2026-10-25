import asyncio
from collections.abc import Callable, Sequence
from typing import TypeVar

from openrgb import OpenRGBClient
from openrgb.orgb import Device
from openrgb.utils import OpenRGBDisconnected, RGBColor, SDKVersionError

from rgb_effects.color import Color
from rgb_effects.config import ServerConfig
from rgb_effects.render.geometry import KeyboardLayout
from rgb_effects.errors import KeyboardUnavailableError

SDK_ERRORS = (OSError, OpenRGBDisconnected, SDKVersionError)
CALL_TIMEOUT_SECONDS = 15.0
DIRECT_MODE = "Direct"

Result = TypeVar("Result")


def layout_of(device: Device) -> KeyboardLayout:
    offset = 0
    matrix: tuple[tuple[int | None, ...], ...] = ()
    for zone in device.zones:
        if zone.matrix_map:
            matrix = tuple(
                tuple(None if cell is None else cell + offset for cell in row)
                for row in zone.matrix_map
            )
            break
        offset += len(zone.leds)
    return KeyboardLayout(tuple(led.name for led in device.leds), matrix)


class OpenRgbKeyboard:
    def __init__(self, server: ServerConfig, device_name: str, client_name: str) -> None:
        self._server = server
        self._device_name = device_name
        self._client_name = client_name
        self._client: OpenRGBClient | None = None
        self._device: Device | None = None

    async def connect(self) -> KeyboardLayout:
        await self.close()
        self._client, self._device = await self._call(self._open)
        return layout_of(self._device)

    async def show(self, colors: Sequence[Color]) -> None:
        device = self._device
        if device is None:
            raise KeyboardUnavailableError("keyboard is not connected")
        payload = [RGBColor(color.red, color.green, color.blue) for color in colors]
        await self._call(lambda: device.set_colors(payload, fast=True))

    async def close(self) -> None:
        client = self._client
        self._client = None
        self._device = None
        if client is not None:
            await self._call(client.disconnect)

    def _open(self) -> tuple[OpenRGBClient, Device]:
        client = OpenRGBClient(self._server.host, self._server.port, self._client_name)
        matches = [device for device in client.devices if device.name == self._device_name]
        if not matches:
            client.disconnect()
            raise KeyboardUnavailableError(f"device {self._device_name!r} is not detected")
        device = matches[0]
        device.set_mode(DIRECT_MODE)
        return client, device

    async def _call(self, action: Callable[[], Result]) -> Result:
        try:
            async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                return await asyncio.to_thread(action)
        except TimeoutError as err:
            raise KeyboardUnavailableError("OpenRGB SDK call timed out") from err
        except SDK_ERRORS as err:
            raise KeyboardUnavailableError("OpenRGB SDK call failed") from err
