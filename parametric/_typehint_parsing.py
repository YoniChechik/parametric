from enum import Enum
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Tuple, Union, get_args, get_origin

from parametric._abstract_base_params import AbstractBaseParams
from parametric._type_node import (
    BaseParamsNode,
    BoolNode,
    BytesNode,
    ComplexNode,
    EnumNode,
    FloatNode,
    IntNode,
    LiteralNode,
    NoneTypeNode,
    PathNode,
    StrNode,
    TupleNode,
    TypeNode,
    UnionNode,
)


class EllipsisTypeError(Exception):
    def __init__(self, name: str):
        super().__init__(
            f"Ellipsis (`...`) is only allowed in this typehint format `tuple(x, ...)`, cannot convert '{name}'"
        )


def parse_typehint(name: str, typehint: Any) -> TypeNode:
    if typehint == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{name}'")

    if typehint is Ellipsis:
        raise EllipsisTypeError(name)

    if typehint is int:
        return IntNode()
    if typehint is float:
        return FloatNode()
    if typehint is bool:
        return BoolNode()
    if typehint is str:
        return StrNode()
    if typehint is bytes:
        return BytesNode()
    if typehint is Path:
        return PathNode()
    if typehint is type(None):
        return NoneTypeNode()
    if typehint is complex:
        return ComplexNode()

    # ==== complex types
    outer_type = get_origin(typehint)
    inner_args = get_args(typehint)

    _validate_complex_type(name, typehint, outer_type, inner_args)

    if outer_type in {Union, UnionType}:
        return UnionNode([parse_typehint(name, arg) for arg in inner_args])

    if outer_type in {tuple, Tuple}:
        parsed_args = []
        is_ends_with_ellipsis = False
        for idx, arg in enumerate(inner_args):
            try:
                parsed_args.append(parse_typehint(name, arg))
            except EllipsisTypeError as e:
                if (len(inner_args) == 2) and (idx == 1):
                    is_ends_with_ellipsis = True
                else:
                    raise e  # Re-raise the error if Ellipsis is not the last element
        return TupleNode(parsed_args, is_ends_with_ellipsis=is_ends_with_ellipsis)

    if outer_type is Literal:
        return LiteralNode(inner_args)

    # ==== derived classes
    if isinstance(typehint, type(Enum)):
        return EnumNode(typehint)

    if issubclass(typehint, AbstractBaseParams):
        return BaseParamsNode(typehint)

    # ==== Raise error if the type is not handled
    raise ValueError(
        f"Parameter '{name}' must be one of the following: a subclass of BaseParams, an immutable type (tuple, "
        f"Literal, Enum, int, float, bool, complex, str, bytes, pathlib.Path, NoneType), or a union of these types."
    )


def _validate_complex_type(name: str, typehint: Any, outer_type: Any, inner_args: tuple):
    """Validates complex types before processing."""
    if typehint is Union and outer_type is None:
        raise ValueError(f"Type hint for {name} cannot be 'Union' without specifying element types")

    if typehint is tuple and outer_type is None:
        raise ValueError(f"Type hint for {name} cannot be 'tuple' without specifying element types")

    if typehint is Tuple and len(inner_args) == 0:
        raise ValueError(f"Type hint for {name} cannot be 'Tuple' without specifying element types")
