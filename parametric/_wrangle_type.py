from types import UnionType
from typing import Any, Tuple, Union, get_args, get_origin

from parametric._const import _EMPTY_FIELD, _IMMUTABLE_BASE_TYPES


def _handle_base_type(value: Any, target_type: Any) -> tuple[Any, bool]:
    """Handles conversion for immutable base types."""
    if isinstance(value, target_type):
        return value, False  # Success, no coercion needed
    try:
        return target_type(value), True  # Success, coercion successful
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value} to {target_type}")


def _handle_union_type(field_name: str, value: Any, target_type: Any, inner_types: tuple[Any, ...]) -> tuple[Any, bool]:
    """Handles conversion for Union types."""
    best_result = _EMPTY_FIELD

    for inner_type in inner_types:
        try:
            result, coerced = wrangle_type(field_name, value, inner_type)
            if not coerced:
                return result, False  # Return immediately if no coercion was needed
            if best_result == _EMPTY_FIELD or coerced:
                best_result = result
        except (ValueError, TypeError):
            continue

    if best_result != _EMPTY_FIELD:
        return best_result, True  # Return the best result, noting that coercion was needed
    raise ValueError(f"Cannot convert {value} to any of the types in {target_type}")


def _handle_tuple_type(field_name: str, value: Any, target_type: Any, inner_types: tuple[Any, ...]) -> tuple[Any, bool]:
    """Handles conversion for Tuple types."""
    if inner_types[-1] is Ellipsis:
        elem_type = inner_types[0]
        results = [wrangle_type(field_name, v, elem_type) for v in value]
    else:
        results = [wrangle_type(field_name, v, t) for v, t in zip(value, inner_types)]

    # Determine if any element was coerced
    coerced = any(r[1] for r in results)
    return tuple(r[0] for r in results), coerced


def _validate_complex_type(field_name: str, target_type: Any, origin_type: Any, inner_types: tuple[Any, ...]):
    """Validates complex types before processing."""

    if target_type is Union and origin_type is None:
        raise ValueError(f"Type hint for {field_name} cannot be 'Union' without specifying element types")

    if target_type is tuple and origin_type is None:
        raise ValueError(f"Type hint for {field_name} cannot be 'tuple' without specifying element types")

    if target_type is Tuple and len(inner_types) == 0:
        raise ValueError(f"Type hint for {field_name} cannot be 'Tuple' without specifying element types")


def wrangle_type(field_name: str, value: Any, target_type: Any) -> tuple[Any, bool]:
    if target_type == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{field_name}'")

    if target_type in _IMMUTABLE_BASE_TYPES:
        return _handle_base_type(value, target_type)

    origin_type = get_origin(target_type)
    inner_types = get_args(target_type)

    _validate_complex_type(field_name, target_type, origin_type, inner_types)

    if origin_type in {Union, UnionType}:
        return _handle_union_type(field_name, value, target_type, inner_types)

    if origin_type in {tuple, Tuple}:
        return _handle_tuple_type(field_name, value, target_type, inner_types)

    raise ValueError(
        f"Field {field_name} should have only this immutable typehints: tuple, {', '.join(t.__name__ for t in _IMMUTABLE_BASE_TYPES)}"
    )
