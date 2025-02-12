import enum
from pathlib import Path
from typing import Any

import numpy as np


# TODO can use encoder decoder of pyyaml
def yaml_custom_encode(value: Any) -> Any:
    # === path to str
    if isinstance(value, Path):
        return str(value.as_posix())
    # === numpy to list
    if isinstance(value, np.ndarray):
        return value.tolist()
    # === tuple (recursively)
    if isinstance(value, tuple):
        return tuple(yaml_custom_encode(item) for item in value)
    from ._base_params import BaseParams

    if isinstance(value, BaseParams):
        return {name: yaml_custom_encode(getattr(value, name)) for name in value._get_annotations()}
    return value


# ====== msgpack


def msgpack_custom_encode(obj):
    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        return {
            "__ndarray__": True,
            "data": obj.data,  # memoryview
            "dtype": str(obj.dtype),
            "shape": obj.shape,
        }
    # Handle pathlib.Path
    if isinstance(obj, Path):
        return {
            "__pathlib__": True,
            "as_posix": str(obj.as_posix()),
        }
    # Handle sequence types
    if isinstance(obj, (tuple, set, list)):
        return {
            "__sequence__": True,
            "type": type(obj).__name__,
            "data": [msgpack_custom_encode(i) for i in obj],
        }
    # Handle Enums by taking their value
    if isinstance(obj, enum.Enum):
        return {
            "__enum__": True,
            "value": obj.value,
        }
    if isinstance(obj, dict):
        return {
            "__dict__": True,
            "data": {k: msgpack_custom_encode(v) for k, v in obj.items()},
        }
    from ._base_params import BaseParams

    if issubclass(type(obj), BaseParams):
        return {
            "__BaseParams__": True,
            "data": {name: msgpack_custom_encode(getattr(obj, name)) for name in obj._get_annotations()},
        }

    return obj


def msgpack_custom_decode(obj: Any) -> Any:
    if isinstance(obj, (int, float, bool, str)):
        return obj
    # Handle numpy arrays
    if "__ndarray__" in obj:
        array = np.frombuffer(obj["data"], dtype=obj["dtype"])
        return array.reshape(obj["shape"])

    # Handle pathlib.Path
    if "__pathlib__" in obj:
        return Path(obj["as_posix"])
    # Handle sequence types
    if "__sequence__" in obj:
        seq_type = {"tuple": tuple, "set": set, "list": list}[obj["type"]]
        return seq_type(obj["data"])
    if "__dict__" in obj:
        return {k: msgpack_custom_decode(v) for k, v in obj["data"].items()}
    # NOTE: don't check enums or basparams because we need to specify the exact class which we do later
    # if "__BaseParams__" in obj:
    #     return obj["data"]
    # if "__enum__" in obj:
    #     return enum.Enum(obj["value"])
    return obj
