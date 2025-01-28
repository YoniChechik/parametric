import enum
from pathlib import Path

import numpy as np


def decode_custom(obj):
    # Handle numpy arrays
    if "__ndarray__" in obj:
        array = np.frombuffer(obj["data"], dtype=obj["dtype"])
        return array.reshape(obj["shape"])
    # Handle pathlib.Path
    if "__pathlib__" in obj:
        return Path(obj["as_posix"])
    return obj


def encode_custom(obj):
    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        return {
            "__ndarray__": True,
            "data": obj.tobytes(),
            "dtype": str(obj.dtype),
            "shape": obj.shape,
        }
    # Handle pathlib.Path
    if isinstance(obj, Path):
        return {
            "__pathlib__": True,
            "as_posix": str(obj.as_posix()),
        }
    # Handle Enums by taking their value
    if isinstance(obj, enum.Enum):
        return obj.value
    return obj
