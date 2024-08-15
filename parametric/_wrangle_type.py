from dataclasses import dataclass
from enum import Enum
from types import UnionType
from typing import Any, Literal, Tuple, Union, get_args, get_origin

from parametric._const import EMPTY_PARAM, IMMUTABLE_BASE_TYPES


@dataclass
class WrangleTypeReturn:
    converted_value: Any
    is_coerced: bool

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, WrangleTypeReturn):
            return False
        return (self.converted_value == other.converted_value) and (self.is_coerced == other.is_coerced)


def wrangle_type(param_name: str, value: Any, target_type: Any) -> WrangleTypeReturn:
    if target_type == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{param_name}'")

    if target_type in IMMUTABLE_BASE_TYPES:
        return _handle_base_type(value, target_type)

    # ==== complex types
    outer_type = get_origin(target_type)
    inner_args = get_args(target_type)

    _validate_complex_type(param_name, target_type, outer_type, inner_args)

    if outer_type in {Union, UnionType}:
        return _handle_union_type(param_name, value, target_type, inner_args)

    if outer_type in {tuple, Tuple}:
        return _handle_tuple_type(param_name, value, inner_args)

    if outer_type is Literal:
        return _handle_literal_type(param_name, value, inner_args)

    # ==== subclasses
    if isinstance(target_type, type(Enum)):
        return _handle_enum_type(param_name, value, target_type)

    # NOTE: this import is here to avoid circular imports
    from parametric._base_params import BaseParams

    if isinstance(target_type, type(BaseParams)):
        return _handle_baseparams_type(param_name, value, target_type)

    # ==== Raise error if the type is not handled
    raise ValueError(
        f"Parameter '{param_name}' must be one of the following: a subclass of BaseParams, an immutable type (such as tuple, "
        f"Literal, Enum, {', '.join(t.__name__ for t in IMMUTABLE_BASE_TYPES)}), or a union of these types."
    )


def _handle_baseparams_type(param_name: str, value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for subclasses of BaseParams."""
    if isinstance(value, target_type):
        return WrangleTypeReturn(value, False)

    if isinstance(value, dict):
        instance = target_type()
        instance.override_from_dict(value)
        return WrangleTypeReturn(instance, True)

    raise ValueError(f"Cannot convert {value} in parameter '{param_name}' to {target_type}")


@dataclass
class WrangleTypeReturn:
    converted_value: Any
    is_coerced: bool

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, WrangleTypeReturn):
            return False
        return (self.converted_value == other.converted_value) and (self.is_coerced == other.is_coerced)


def wrangle_type(field_name: str, value: Any, target_type: Any) -> WrangleTypeReturn:
    if target_type == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{field_name}'")

    if target_type in IMMUTABLE_BASE_TYPES:
        return _handle_base_type(value, target_type)

    # ==== complex types
    outer_type = get_origin(target_type)
    inner_args = get_args(target_type)

    _validate_complex_type(field_name, target_type, outer_type, inner_args)

    if outer_type in {Union, UnionType}:
        return _handle_union_type(field_name, value, target_type, inner_args)

    if outer_type in {tuple, Tuple}:
        return _handle_tuple_type(field_name, value, inner_args)

    if outer_type is Literal:
        return _handle_literal_type(field_name, value, inner_args)

    # ==== subclasses
    if issubclass(target_type, Enum):
        return _handle_enum_type(field_name, value, target_type)

    # ==== Raise error if the type is not handled
    raise ValueError(
        f"Field '{field_name}' must be one of the following: a subclass of BaseParams, an immutable type (such as tuple, "
        f"Literal, Enum, {', '.join(t.__name__ for t in IMMUTABLE_BASE_TYPES)}), or a union of these types."
    )


def _handle_base_type(value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for immutable base types."""
    if isinstance(value, target_type):
        return WrangleTypeReturn(value, False)
    try:
        return WrangleTypeReturn(target_type(value), True)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value} to {target_type}")


def _handle_literal_type(param_name: str, value: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Literal types."""
    if value in inner_args:
        return WrangleTypeReturn(value, False)
    raise ValueError(f"Cannot convert {value} in parameter '{param_name}' to one of possible literals {inner_args}")


def _handle_enum_type(param_name: str, value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for Enum types."""
    if isinstance(value, target_type):
        return WrangleTypeReturn(value, False)
    try:
        return WrangleTypeReturn(target_type(value), True)
    except ValueError:
        raise ValueError(f"Cannot convert {value} in parameter '{param_name}' to Enum {target_type}")


def _handle_union_type(param_name: str, value: Any, target_type: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Union types."""
    best_result = EMPTY_PARAM

    for inner_type in inner_args:
        try:
            wrangle_type_return = wrangle_type(param_name, value, inner_type)
            if not wrangle_type_return.is_coerced:
                return wrangle_type_return
            if best_result == EMPTY_PARAM or wrangle_type_return.is_coerced:
                best_result = wrangle_type_return.converted_value
        except (ValueError, TypeError):
            continue

    if best_result != EMPTY_PARAM:
        return WrangleTypeReturn(best_result, True)
    raise ValueError(f"Cannot convert {value} to any of the types in {target_type}")


def _handle_tuple_type(param_name: str, value: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Tuple types."""
    if inner_args[-1] is Ellipsis:
        elem_type = inner_args[0]
        results = [wrangle_type(param_name, v, elem_type) for v in value]
    else:
        results = [wrangle_type(param_name, v, t) for v, t in zip(value, inner_args)]

    # Determine if any element was coerced
    coerced = any(r.is_coerced for r in results)
    return WrangleTypeReturn(tuple(r.converted_value for r in results), coerced)

def _validate_complex_type(param_name: str, target_type: Any, outer_type: Any, inner_args: tuple):
    """Validates complex types before processing."""
    if target_type is Union and outer_type is None:
        raise ValueError(f"Type hint for {param_name} cannot be 'Union' without specifying element types")

    if target_type is tuple and outer_type is None:
        raise ValueError(f"Type hint for {param_name} cannot be 'tuple' without specifying element types")

    if target_type is Tuple and len(inner_args) == 0:
        raise ValueError(f"Type hint for {param_name} cannot be 'Tuple' without specifying element types")
