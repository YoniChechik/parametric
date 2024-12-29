import enum
from collections import deque
from pathlib import Path
from types import GeneratorType, UnionType
from typing import Any, Literal, Type, Union, get_origin

import numpy as np
from typing_extensions import get_args


def _validate_immutable_annotation_and_coerce_np(name: str, annotation: Type, value: Any) -> None:
    if annotation == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{name}'")

    if annotation is Ellipsis:
        raise ValueError(
            f"Ellipsis (`...`) is only allowed in this type format `tuple(x, ...)`, cannot convert '{name}'"
        )

    # ==== basic types
    if annotation in {int, float, bool, str, bytes, Path, type(None)}:
        return

    # == enums
    if isinstance(annotation, enum.EnumMeta):
        return

    # ==== BaseParams
    # NOTE: This import is here to avoid circular imports
    from parametric import BaseParams

    try:
        if issubclass(annotation, BaseParams):
            return
    except Exception:
        pass

    # ==== complex types
    outer_type = get_origin(annotation)
    inner_types = get_args(annotation)

    # ===== old types are bad
    try:
        if annotation._name == "Tuple":
            raise ValueError("Old Tuple[x,y,z] type is bad practice. Use tuple[x,y,z] instead.")
        if annotation._name == "Optional":
            raise ValueError("Old Optional[x] type is bad practice. Use x | None instead.")
    except AttributeError:
        pass
    if outer_type is Union or annotation is Union:
        raise ValueError("Old Union[x,y,z] type is bad practice. Use x | y | z instead.")

    # == numpy
    if annotation is np.array or outer_type is np.array:
        raise ValueError(f"Type of {name} cannot be 'np.array'. Try np.ndarray[int] instead")

    if annotation is np.ndarray:
        raise ValueError(
            f"Type of {name} cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])"
        )
    if outer_type is np.ndarray:
        if len(inner_types) != 1:
            raise ValueError(f"dtype of 'np.ndarray' {name} should have exactly 1 inner args (e.g. np.ndarray[int])")

        arr_dtype = inner_types[0]
        _validate_immutable_annotation_and_coerce_np(name, arr_dtype, value)
        if arr_dtype is type(None):
            raise ValueError(f"dtype of 'np.ndarray' {name} cannot be NoneType")
        if get_origin(arr_dtype) in {UnionType, tuple}:
            raise ValueError(f"dtype of 'np.ndarray' {name} cannot be Union or Tuple")

        arr = np.array(value, dtype=inner_types[0])
        arr.flags.writeable = False
        return arr

    # == union
    if outer_type is UnionType:
        res_to_return = None
        for arg in inner_types:
            tmp_res = _validate_immutable_annotation_and_coerce_np(name, arg, value)
            if res_to_return is None:
                res_to_return = tmp_res

        # type checks passed, now check for union of common types
        is_basic_type_already_exist = False
        is_np_exist = False
        is_tuple_exist = False
        for arg in inner_types:
            outer_arg = get_origin(arg)
            if outer_arg is np.ndarray:
                is_np_exist = True
                if is_tuple_exist:
                    raise ValueError(
                        "Union of numpy and tuple is bad practice since their serialization can be similar"
                    )
            if outer_arg is tuple:
                is_tuple_exist = True
                if is_np_exist:
                    raise ValueError(
                        "Union of numpy and tuple is bad practice since their serialization can be similar"
                    )

            if arg in {type(None), tuple}:
                continue
            if is_basic_type_already_exist:
                raise ValueError(
                    "Union of common types is bad practice. You can use None and tuple and ONE other type in unions"
                )
            is_basic_type_already_exist = True
        return res_to_return

    # == tuple
    if annotation is tuple and outer_type is None:
        raise ValueError(f"Type of {name} cannot be 'tuple' without specifying element types (e.g. tuple[int, str])")

    if outer_type is tuple:
        if not isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque)):
            raise ValueError(f"In {name}, {type(value)} is not tuple compatible.")

        is_end_with_elipsis = False
        if inner_types[-1] is Ellipsis:
            if len(inner_types) != 2:
                raise ValueError(f"when using Ellipsis in {name}, only one inner type is allowed, e.g. tuple[int, ...]")
            is_end_with_elipsis = True
        elif len(inner_types) != len(value):
            raise ValueError(f"Expected in {name} a tuple of length {len(inner_types)}, got {len(value)}")

        res = []
        is_np_inside = False
        for i, val_i in enumerate(value):
            curr_inner_type = inner_types[0] if is_end_with_elipsis else inner_types[i]
            arg_res = _validate_immutable_annotation_and_coerce_np(name, curr_inner_type, val_i)

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

    # ==== Raise error if the type is not handled
    raise ValueError(
        f"Parameter '{name}' must be one of the following: a subclass of BaseParams, an immutable type (tuple, np.ndarray, "
        f"Literal, Enum, int, float, bool, str, bytes, pathlib.Path, NoneType), or a union of these types."
    )
