import enum
from typing import Any

import numpy as np


def is_equal_field(val1: Any, val2: Any) -> bool:
    # for enums
    if isinstance(val1, enum.Enum) and isinstance(val2, enum.Enum):
        return val1.value == val2.value
    # for np.ndarray
    if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
        return np.array_equal(val1, val2)
    # for all others
    if val1 == val2:
        return True
    return False
