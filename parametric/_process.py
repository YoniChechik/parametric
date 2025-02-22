import enum
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from types import GeneratorType, UnionType
from typing import Any, Literal, Type, TypeVar, Union, get_args, get_origin

import numpy as np

# TODO remove constrainet for tuple[x].
T = TypeVar("T")

ALLOWED_NUMPY_TYPES = {
    np.int8,
    np.int16,
    np.int32,
    np.int64,
    np.uint8,
    np.uint16,
    np.uint32,
    np.uint64,
    np.float16,
    np.float32,
    np.float64,
}


class _ProcessingResult:
    def __init__(self, *, is_coerced: bool, coerced_value: Any = None):
        self.is_coerced = is_coerced
        self.coerced_value = coerced_value


class BaseProcessor(ABC):
    @abstractmethod
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        pass


class BasicTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        if not (annotation in {int, float, bool, str, bytes, Path, type(None)} or annotation in ALLOWED_NUMPY_TYPES):
            return None

        if isinstance(value, annotation):
            return _ProcessingResult(is_coerced=False)
        try:
            return _ProcessingResult(is_coerced=True, coerced_value=annotation(value))
        except (ValueError, TypeError) as e:
            raise TypeError(f"Could not coerce value '{value}' to type {annotation}: {str(e)}")


class EnumProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        if not isinstance(annotation, enum.EnumMeta):
            return None

        if isinstance(value, annotation):
            return _ProcessingResult(is_coerced=False)
        try:
            return _ProcessingResult(is_coerced=True, coerced_value=annotation(value))
        except Exception as e:
            raise TypeError(f"Could not coerce value '{value}' to type {annotation}: {str(e)}")


class UnionTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        if get_origin(annotation) is not UnionType:
            return None

        inner_types = get_args(annotation)
        errors = []

        # Try conversions
        for arg in inner_types:
            try:
                # TODO fix here
                result = process_field(name, arg, value, strict=strict)
                if result is not None:
                    return result  # Already a _ProcessingResult
            except Exception as e:
                errors.append(str(e))

        # If we get here, all conversions failed
        error_details = "\n".join(f"- {err}" for err in errors)
        raise ValueError(
            f"Could not convert value '{value}' to any of the union types for parameter '{name}'. "
            f"Attempted conversions failed with:\n{error_details}"
        )


class LiteralTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        if get_origin(annotation) is not Literal:
            return None

        inner_types = get_args(annotation)
        if not inner_types:
            raise ValueError(f"Literal type for {name} must have at least one value")

        # Check that all inner types are valid literal types
        valid_literal_types = (str, int, bool, float, enum.Enum, type(None))
        for arg in inner_types:
            if not isinstance(arg, valid_literal_types):
                raise ValueError(
                    f"Literal values in {name} must be strings, numbers, booleans, enums, or None. Got {type(arg)}"
                )

        if value not in inner_types:
            options_str = ", ".join(str(opt) for opt in inner_types)
            raise ValueError(f"Value {value} for {name} must be one of the literal options: {options_str}")

        return _ProcessingResult(is_coerced=False, coerced_value=None)


class DictTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        outer_type = get_origin(annotation)
        if annotation is dict and outer_type is None:
            raise ValueError(
                f"Type of {name} cannot be 'dict' without specifying key and value types (e.g. dict[str, int])"
            )

        if outer_type is not dict:
            return None

        if not isinstance(value, dict):
            raise ValueError(f"In {name}, {type(value)} is not dict compatible.")

        inner_types = get_args(annotation)
        if len(inner_types) != 2:
            raise ValueError(f"dict type {name} must have exactly 2 type arguments (key and value types)")

        key_type, value_type = inner_types
        res = {}

        for k, v in value.items():
            key_result = process_field(f"{name} key", key_type, k, strict=strict)
            value_result = process_field(f"{name} value", value_type, v, strict=strict)

            key = key_result.coerced_value if key_result is not None and key_result.is_coerced else k
            val = value_result.coerced_value if value_result is not None and value_result.is_coerced else v
            res[key] = val

        return _ProcessingResult(is_coerced=True, coerced_value=res)


def _process_sequence_elements(name: str, value: Any, inner_types: tuple, strict: bool, *, is_variadic: bool) -> list:
    """Common helper function to process sequence elements."""
    res = []
    for i, val_i in enumerate(value):
        curr_inner_type = inner_types[0] if is_variadic else inner_types[i]
        result = process_field(name, curr_inner_type, val_i, strict=strict)
        res.append(result.coerced_value if result.is_coerced else val_i)
    return res


def _validate_sequence_value(name: str, value: Any):
    """Common validation for sequence-like values."""
    if not isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque)):
        raise ValueError(f"In {name}, {type(value)} is not sequence compatible.")


class ListTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        outer_type = get_origin(annotation) or annotation
        if outer_type is not list:
            return None

        _validate_sequence_value(name, value)
        inner_types = get_args(annotation)

        if len(inner_types) > 2 or (len(inner_types) == 2 and inner_types[-1] is not Ellipsis):
            raise ValueError(f"list type {name} must have exactly 1 type argument (e.g. list[int])")

        is_variadic = inner_types[-1] is Ellipsis or len(inner_types) == 1
        result = _process_sequence_elements(name, value, inner_types, strict, is_variadic=is_variadic)

        return _ProcessingResult(is_coerced=True, coerced_value=list(result))


class TupleTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        outer_type = get_origin(annotation) or annotation
        if outer_type is not tuple:
            return None

        _validate_sequence_value(name, value)
        inner_types = get_args(annotation)

        if inner_types is None:
            return _ProcessingResult(is_coerced=True, coerced_value=value)

        is_variadic = inner_types[-1] is Ellipsis
        if is_variadic:
            if len(inner_types) != 2:
                raise ValueError(f"when using Ellipsis in {name}, only one inner type is allowed, e.g. tuple[int, ...]")
        elif len(inner_types) != len(value):
            raise ValueError(f"Expected in {name} a tuple of length {len(inner_types)}, got {len(value)}")

        result = _process_sequence_elements(name, value, inner_types, strict, is_variadic=is_variadic)
        return _ProcessingResult(is_coerced=True, coerced_value=tuple(result))


class SetTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        outer_type = get_origin(annotation) or annotation
        if outer_type is not set:
            return None

        _validate_sequence_value(name, value)
        inner_types = get_args(annotation)

        if len(inner_types) > 2 or (len(inner_types) == 2 and inner_types[-1] is not Ellipsis):
            raise ValueError(f"set type {name} must have exactly 1 type argument (e.g. set[int])")

        is_variadic = inner_types[-1] is Ellipsis or len(inner_types) == 1
        result = _process_sequence_elements(name, value, inner_types, strict, is_variadic=is_variadic)

        return _ProcessingResult(is_coerced=True, coerced_value=set(result))


class NumpyTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        outer_type = get_origin(annotation) or annotation
        if outer_type is not np.ndarray:
            return None

        inner_types = get_args(annotation)

        if not isinstance(value, (list, tuple, np.ndarray)):
            raise ValueError(f"Value for numpy array parameter '{name}' must be array-like (list, tuple, or ndarray)")

        if len(inner_types) > 1:
            raise ValueError(f"dtype of 'np.ndarray' {name} should have at most 1 inner arg (e.g. np.ndarray[int])")
        if len(inner_types) == 0:
            return _ProcessingResult(is_coerced=True, coerced_value=np.asarray(value))
        if len(inner_types) == 1:
            arr_dtype = inner_types[0]

            # Check for allowed numpy dtypes
            allowed_dtypes = {int, float, bool}
            allowed_dtypes.update(ALLOWED_NUMPY_TYPES)

            if arr_dtype not in allowed_dtypes:
                raise ValueError(
                    f"dtype of 'np.ndarray' {name} must be one of the allowed types: "
                    f"{', '.join(str(dtype.__name__) for dtype in allowed_dtypes)}"
                )

            return _ProcessingResult(is_coerced=True, coerced_value=np.asarray(value, dtype=arr_dtype))


class BaseParamsProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult | None:
        # avoid circular import
        from parametric import BaseParams

        try:
            if issubclass(annotation, BaseParams):
                if isinstance(value, BaseParams):
                    return _ProcessingResult(is_coerced=False)
                else:
                    raise ValueError(f"Parameter '{name}' must be a subclass of BaseParams")
        except TypeError:
            pass
        return None


def process_field(name: str, annotation: Type[T], value: Any, strict: bool) -> _ProcessingResult | None:
    if name == "np04":
        print(f"processing {name} with {annotation} and {value}")
    if annotation == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{name}'")

    if annotation is Ellipsis:
        raise ValueError(
            f"Ellipsis (`...`) is only allowed in this type format `tuple(x, ...)`, cannot convert '{name}'"
        )

    # Check old style type hints
    try:
        if annotation._name == "Tuple":
            raise ValueError("Old Tuple[x,y,z] type is bad practice. Use tuple[x,y,z] instead.")
        if annotation._name == "Optional":
            raise ValueError("Old Optional[x] type is bad practice. Use x | None instead.")
    except AttributeError:
        pass

    if get_origin(annotation) is Union or annotation is Union:
        raise ValueError("Old Union[x,y,z] type is bad practice. Use x | y | z instead.")

    processors: list[BaseProcessor] = [
        BasicTypeProcessor(),
        EnumProcessor(),
        BaseParamsProcessor(),
        NumpyTypeProcessor(),
        ListTypeProcessor(),
        TupleTypeProcessor(),
        SetTypeProcessor(),
        DictTypeProcessor(),
        UnionTypeProcessor(),
        LiteralTypeProcessor(),
    ]

    for processor in processors:
        result = processor(name, annotation, value, strict)
        if result is not None:
            if isinstance(result, np.ndarray):
                return result
            return result

    raise ValueError(f"Parameter '{name}' does not have a supported type")
