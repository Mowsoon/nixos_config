import math
from collections import Counter

import numpy as np
from numpy.typing import NDArray

from rgb_effects.render.oklab import Floats

Indices = NDArray[np.intp]
FRAME_END_PACKETS = 1
SINGLE_VALUE_ZONES = 13
INDIVIDUAL_ZONES = 4


def packet_cost(counts: Counter[int]) -> int:
    present = [count for count in counts.values() if count > 0]
    if not present:
        return 0
    singles = sum(1 for count in present if count == 1)
    groups = sum(math.ceil(count / SINGLE_VALUE_ZONES) for count in present if count > 1)
    return FRAME_END_PACKETS + groups + math.ceil(singles / INDIVIDUAL_ZONES)


def select_changes(
    changed: Indices, colors: Indices, priority: Indices, error: Floats, max_packets: int
) -> Indices:
    order = changed[np.lexsort((-error[changed], -priority[changed]))]
    counts: Counter[int] = Counter()
    chosen: list[int] = []
    for led in order:
        color = int(colors[led])
        counts[color] += 1
        if packet_cost(counts) > max_packets:
            counts[color] -= 1
            continue
        chosen.append(int(led))
    return np.array(sorted(chosen), dtype=np.intp)
