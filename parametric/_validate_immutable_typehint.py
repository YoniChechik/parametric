from collections import deque
from types import GeneratorType
from typing import Any, Tuple, Type, get_origin

import numpy as np
from typing_extensions import get_args


def _validate_np(type_name: str, typehint: Type, value: Any) -> None:
    outer_type = get_origin(typehint)
    inner_args = get_args(typehint)

    if outer_type is np.array:
        raise ValueError(f"Type hint for {type_name} cannot be 'np.array'. Try np.ndarray[int] instead")

    if outer_type is np.ndarray:
        if len(inner_args) == 0:
            raise ValueError(
                f"Type hint for {type_name} cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])"
            )
        elif len(inner_args) > 1:
            raise ValueError(
                f"Type hint for 'np.ndarray' {type_name} should have exactly 1 inner args (e.g. np.ndarray[int])"
            )
        else:  # valid np.ndarray
            return np.array(value)

    # == union
    # TODO make it currently support either numpy or None
    # if outer_type in {Union, UnionType}:
    #     for arg in inner_args:
    #         _validate_np(type_name, arg)
    #     return

    # == tuple
    if outer_type in {tuple, Tuple}:
        if not isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque)):
            raise ValueError(f"Expected in {type_name} a tuple or tuple compatible, got {type(value)}")

        is_end_with_elipsis = False
        if len(inner_args) == 2 and inner_args[1] is Ellipsis:
            is_end_with_elipsis = True
        elif len(inner_args) != len(value):
            raise ValueError(f"Expected in {type_name} a tuple of length {len(inner_args)}, got {len(value)}")

        res = []
        is_np_inside = False
        for i in range(len(value)):
            curr_inner_type = inner_args[0] if is_end_with_elipsis else inner_args[i]
            arg_res = _validate_np(type_name, curr_inner_type, value[i])
            if arg_res is not None:
                res.append(arg_res)
                is_np_inside = True
            else:
                res.append(value[i])

        if is_np_inside:
            return tuple(res)
        return None
