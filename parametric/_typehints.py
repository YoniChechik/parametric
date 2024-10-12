from pathlib import Path
from types import UnionType
from typing import Literal, Tuple, Type, Union, get_origin

from typing_extensions import get_args


def _validate_immutable_typehint(type_name: str, typehint: Type) -> None:
    # ==== basic types
    if typehint in (int, float, bool, str, bytes, Path, type(None)):
        return

    # ==== complex types
    outer_type = get_origin(typehint)
    inner_args = get_args(typehint)

    # == union
    if outer_type in {Union, UnionType}:
        for arg in inner_args:
            _validate_immutable_typehint(type_name, arg)
        return

    # == tuple
    if outer_type in {tuple, Tuple}:
        if len(inner_args) == 0:
            raise RuntimeError(f"In {type_name}, must declere args for tuple typehint, e.g. tuple[int]")
        if len(inner_args) == 1 and inner_args[0] is Ellipsis:
            raise RuntimeError(f"In {type_name}, tuple typehint cannot have `...` as the only arg")
        for arg in inner_args:
            if arg is Ellipsis:
                continue
            _validate_immutable_typehint(type_name, arg)
        return

    # == literals
    if outer_type is Literal:
        for arg in inner_args:
            _validate_immutable_typehint(type_name, type(arg))
        return

    raise RuntimeError(f"In {type_name}, typehint {typehint} is not allowed because he is not immutable")
