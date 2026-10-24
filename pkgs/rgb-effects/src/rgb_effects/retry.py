import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    initial_seconds: float
    maximum_seconds: float

    def next_delay(self, current: float) -> float:
        return min(current * 2, self.maximum_seconds)

    def jittered(self, delay: float) -> float:
        return delay * (0.5 + secrets.SystemRandom().random())
