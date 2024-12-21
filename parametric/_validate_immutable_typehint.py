import enum
from collections import deque
from pathlib import Path
from types import GeneratorType, GenericAlias, UnionType
from typing import Any, Literal, Tuple, Type, Union, get_origin

import numpy as np
from typing_extensions import get_args


def _validate_immutable_typehint(name: str, typehint: Type, value: Any) -> None:
    if typehint == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{name}'")

    if typehint is Ellipsis:
        raise ValueError(
            f"Ellipsis (`...`) is only allowed in this typehint format `tuple(x, ...)`, cannot convert '{name}'"
        )

    # ==== basic types
    if typehint in (int, float, bool, str, bytes, Path, type(None)):
        return

    # == enums
    if isinstance(typehint, enum.EnumMeta):
        return

    # ==== complex types
    outer_type = get_origin(typehint)
    inner_args = get_args(typehint)

    # == numpy
    if typehint is np.array or outer_type is np.array:
        raise ValueError(f"Type hint for {name} cannot be 'np.array'. Try np.ndarray[int] instead")

    if typehint is np.ndarray:
        raise ValueError(
            f"Type hint for {name} cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])"
        )
    if outer_type is np.ndarray:
        if len(inner_args) != 1:
            raise ValueError(
                f"Type hint for 'np.ndarray' {name} should have exactly 1 inner args (e.g. np.ndarray[int])"
            )

        arr = np.array(value, dtype=inner_args[0])
        arr.flags.writeable = False
        return arr

    # == union
    if typehint is Union and outer_type is None:
        raise ValueError(
            f"Type hint for {name} cannot be 'Union' without specifying element types (e.g. Union[int, str])"
        )

    # TODO support numpy
    if outer_type in {Union, UnionType}:
        for arg in inner_args:
            _validate_immutable_typehint(name, arg, value)
        return

    # == tuple
    if typehint is tuple and outer_type is None:
        raise ValueError(
            f"Type hint for {name} cannot be 'tuple' without specifying element types (e.g. tuple[int, str])"
        )

    if typehint is Tuple and len(inner_args) == 0:
        raise ValueError(
            f"Type hint for {name} cannot be 'Tuple' without specifying element types (e.g. Tuple[int, str])"
        )

    if outer_type in {tuple, Tuple}:
        if not isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque)):
            raise ValueError(f"In {name}, {type(value)} is not tuple compatible.")

        is_end_with_elipsis = False
        if inner_args[-1] is Ellipsis:
            if len(inner_args) != 2:
                raise ValueError(f"when using Ellipsis in {name}, only one inner type is allowed, e.g. tuple[int, ...]")
            is_end_with_elipsis = True
        elif len(inner_args) != len(value):
            raise ValueError(f"Expected in {name} a tuple of length {len(inner_args)}, got {len(value)}")

        res = []
        is_np_inside = False
        for i, val_i in enumerate(value):
            curr_inner_type = inner_args[0] if is_end_with_elipsis else inner_args[i]
            arg_res = _validate_immutable_typehint(name, curr_inner_type, val_i)
            if arg_res is not None:
                res.append(arg_res)
                is_np_inside = True
            else:
                res.append(val_i)

        if is_np_inside:
            return tuple(res)
        return None

    # == Literal
    if outer_type is Literal:
        return

    # ==== BaseParams
    # NOTE: This import is here to avoid circular imports
    from parametric import BaseParams

    # NOTE in python 3.10 generic alias like list[int] can't be check with issubclass
    if not isinstance(typehint, GenericAlias) and issubclass(typehint, BaseParams):
        return

    # ==== Raise error if the type is not handled
    raise ValueError(
        f"Parameter '{name}' must be one of the following: a subclass of BaseParams, an immutable type (tuple, "
        f"Literal, Enum, int, float, bool, complex, str, bytes, pathlib.Path, NoneType), or a union of these types."
    )
