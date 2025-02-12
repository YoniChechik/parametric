import enum
from typing import Any

import numpy as np


def is_equal_field(val1: Any, val2: Any) -> bool:
    # for enums- must check both values are enums in a weird way
    if isinstance(val1, enum.Enum):
        if not isinstance(val2, enum.Enum):
            return False
        if type(val1).__name__ != type(val2).__name__:
            return False
        return val1.value == val2.value

    from parametric._base_params import BaseParams

    if issubclass(type(val1), BaseParams):
        if not issubclass(type(val2), BaseParams):
            return False
        return val1 == val2

    # for np.ndarray
    if isinstance(val1, np.ndarray):
        return np.array_equal(val1, val2)

    # TODO if we'll get the type annotation we can check per field only if np array is there
    # for dictionaries
    if isinstance(val1, dict):
        if set(val1.keys()) != set(val2.keys()):
            return False
        return all(is_equal_field(v, val2[k]) for k, v in val1.items())

    # for sequences
    # NOTE: no need to check set because the input args can only be hashable, meaning a simple set_a==set_b is good enough
    if isinstance(val1, (list, tuple)):
        if len(val1) != len(val2):
            return False
        return all(is_equal_field(v1, v2) for v1, v2 in zip(val1, val2))

    # for all others
    if val1 == val2:
        return True
    return False
