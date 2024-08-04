from enum import Enum
from types import UnionType
from typing import Any, Literal, Tuple, Union, get_args, get_origin

from parametric._const import EMPTY_FIELD, IMMUTABLE_BASE_TYPES


def _handle_base_type(value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for immutable base types."""
    if isinstance(value, target_type):
        return value, False  # Success, no coercion needed
    try:
        return target_type(value), True  # Success, coercion successful
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value} to {target_type}")


def _handle_literal_type(field_name: str, value: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Literal types."""
    if value in inner_args:
        return value, False  # Success, value matches one of the literals
    raise ValueError(f"Cannot convert {value} in field {field_name} to one of possible literals {inner_args}")


def _handle_enum_type(field_name: str, value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for Enum types."""
    if isinstance(value, target_type):
        return value, False  # Success, value is already an enum instance
    try:
        return target_type(value), True  # Try converting to enum
    except ValueError:
        raise ValueError(f"Cannot convert {value} in field {field_name} to Enum {target_type}")


def _handle_union_type(field_name: str, value: Any, target_type: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Union types."""
    best_result = EMPTY_FIELD

    for inner_type in inner_args:
        try:
            result, coerced = wrangle_type(field_name, value, inner_type)
            if not coerced:
                return result, False  # Return immediately if no coercion was needed
            if best_result == EMPTY_FIELD or coerced:
                best_result = result
        except (ValueError, TypeError):
            continue

    if best_result != EMPTY_FIELD:
        return best_result, True  # Return the best result, noting that coercion was needed
    raise ValueError(f"Cannot convert {value} to any of the types in {target_type}")


def _handle_tuple_type(field_name: str, value: Any, target_type: Any, inner_args: tuple) -> tuple[Any, bool]:
    """Handles conversion for Tuple types."""
    if inner_args[-1] is Ellipsis:
        elem_type = inner_args[0]
        results = [wrangle_type(field_name, v, elem_type) for v in value]
    else:
        results = [wrangle_type(field_name, v, t) for v, t in zip(value, inner_args)]

    # Determine if any element was coerced
    coerced = any(r[1] for r in results)
    return tuple(r[0] for r in results), coerced


def _validate_complex_type(field_name: str, target_type: Any, origin_type: Any, inner_args: tuple):
    """Validates complex types before processing."""
    if target_type is Union and origin_type is None:
        raise ValueError(f"Type hint for {field_name} cannot be 'Union' without specifying element types")

    if target_type is tuple and origin_type is None:
        raise ValueError(f"Type hint for {field_name} cannot be 'tuple' without specifying element types")

    if target_type is Tuple and len(inner_args) == 0:
        raise ValueError(f"Type hint for {field_name} cannot be 'Tuple' without specifying element types")


def wrangle_type(field_name: str, value: Any, target_type: Any) -> tuple[Any, bool]:
    if target_type == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{field_name}'")

    if target_type in IMMUTABLE_BASE_TYPES:
        return _handle_base_type(value, target_type)

    origin_type = get_origin(target_type)
    inner_args = get_args(target_type)

    _validate_complex_type(field_name, target_type, origin_type, inner_args)

    if origin_type in {Union, UnionType}:
        return _handle_union_type(field_name, value, target_type, inner_args)

    if origin_type in {tuple, Tuple}:
        return _handle_tuple_type(field_name, value, target_type, inner_args)

    if origin_type is Literal:
        return _handle_literal_type(field_name, value, inner_args)

    if issubclass(target_type, Enum):
        return _handle_enum_type(field_name, value, target_type)

    raise ValueError(
        f"Field {field_name} should have only this immutable typehints or a union of them: "
        f"tuple, Literal, Enum, {', '.join(t.__name__ for t in IMMUTABLE_BASE_TYPES)}"
    )
