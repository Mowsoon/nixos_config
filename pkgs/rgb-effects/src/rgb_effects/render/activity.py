import math


class Activity:
    def __init__(self, time_constant: float, start: float) -> None:
        if time_constant <= 0:
            raise ValueError("activity time constant must be positive")
        self._tau = time_constant
        self._rate = 0.0
        self._updated = start
        self._last_event = start

    @property
    def last_event(self) -> float:
        return self._last_event

    def record(self, now: float) -> None:
        self._decay(now)
        self._rate += 1.0 / self._tau
        self._last_event = now

    def rate(self, now: float) -> float:
        self._decay(now)
        return self._rate

    def idle_for(self, now: float) -> float:
        return max(0.0, now - self._last_event)

    def _decay(self, now: float) -> None:
        elapsed = max(0.0, now - self._updated)
        self._rate *= math.exp(-elapsed / self._tau)
        self._updated = now
