import enum
from pathlib import Path
from types import UnionType
from typing import Literal, Tuple, Type, Union, get_origin

from typing_extensions import get_args


def _validate_immutable_typehint(type_name: str, typehint: Type) -> None:
    # ==== basic types
    if typehint in (int, float, bool, str, bytes, Path, type(None)):
        return

    # == enums
    if isinstance(typehint, enum.EnumMeta):
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
    # NOTE: this way you check empty tuple. outer_type & inner_args are None
    if typehint in {tuple, Tuple}:
        _raise_empty_tuple(type_name)

    if outer_type in {tuple, Tuple}:
        # NOTE: this state is already covered in pydantic
        # if len(inner_args) == 1 and inner_args[0] is Ellipsis:
        #     raise RuntimeError(f"In {type_name}, tuple typehint cannot have `...` as the only arg")
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

    raise RuntimeError(f"Can't create {type_name}. Typehint {typehint} is not allowed because it is not immutable")


def _raise_empty_tuple(type_name):
    raise RuntimeError(f"Can't create {type_name}. You must declere args for tuple typehint, e.g. tuple[int]")
