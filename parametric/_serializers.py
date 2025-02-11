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
    from _base_params import BaseParams

    if isinstance(value, BaseParams):
        return {name: yaml_custom_encode(getattr(value, name)) for name in value._get_annotations()}
    return value
