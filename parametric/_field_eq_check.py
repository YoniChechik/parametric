import enum
from typing import Any

import numpy as np


def is_equal_field(val1: Any, val2: Any) -> bool:
    if type(val1) is not type(val2):
        return False

    # for enums
    if isinstance(val1, enum.Enum):
        return val1.value == val2.value

    # for np.ndarray
    if isinstance(val1, np.ndarray):
        return np.array_equal(val1, val2)

    # TODO if we'll get the type annotation we can check per field only if np array is there
    # for dictionaries
    if isinstance(val1, dict):
        if set(val1.keys()) != set(val2.keys()):
            return False
        return all(is_equal_field(v, val2[k]) for k, v in val1.items())

    if isinstance(val1, (list, tuple, set)):
        if len(val1) != len(val2):
            return False
        return all(is_equal_field(v1, v2) for v1, v2 in zip(val1, val2))

    # for all others
    if val1 == val2:
        return True
    return False
