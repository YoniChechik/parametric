import enum
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from types import GeneratorType, UnionType
from typing import Any, Literal, Type, TypeVar, Union, get_args, get_origin

import numpy as np

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
    def __init__(self, /, is_checked_type: bool, is_coerced: bool = False, coerced_value: Any = None):
        self.is_checked_type = is_checked_type
        self.is_coerced = is_coerced
        self.coerced_value = coerced_value


class BaseProcessor(ABC):
    @abstractmethod
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
        pass


class BasicTypeProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
        if annotation in {int, float, bool, str, bytes, Path, type(None)} or annotation in ALLOWED_NUMPY_TYPES:
            if isinstance(value, annotation):
                return _ProcessingResult(True)
            try:
                return _ProcessingResult(True, True, annotation(value))
            except (ValueError, TypeError) as e:
                raise TypeError(f"Could not coerce value '{value}' to type {annotation}: {str(e)}")
        return _ProcessingResult(False, False, None)


class EnumProcessor(BaseProcessor):
    def __call__(self, name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
        try:
            if issubclass(annotation, enum.Enum):
                try:
                    return _ProcessingResult(True, True, annotation(value))
                except (ValueError, TypeError) as e:
                    raise TypeError(f"Could not coerce value '{value}' to type {annotation}: {str(e)}")
        except TypeError:
            pass
        return _ProcessingResult(False, False, None)


def process_field(name: str, annotation: Type[T], value: Any, strict: bool) -> T | None:
    if annotation == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{name}'")

    if annotation is Ellipsis:
        raise ValueError(
            f"Ellipsis (`...`) is only allowed in this type format `tuple(x, ...)`, cannot convert '{name}'"
        )

    processors = [
        BasicTypeProcessor(),
        EnumProcessor(),
        # Add other processors here
    ]

    for processor in processors:
        result = processor(name, annotation, value, strict)
        if result.is_checked_type:
            return result.coerced_value if result.is_coerced else value

    # Continue with remaining processing...
    outer_type = get_origin(annotation)

    # BaseParams
    base_params_result = _process_base_params_type(name, annotation, value, strict)
    if base_params_result.is_checked_type:
        return base_params_result.coerced_value if base_params_result.is_coerced else value

    # Check old style type hints
    _process_old_style_types(annotation, outer_type)

    # Process numpy arrays
    numpy_result = _process_numpy_type(name, annotation, value, strict)
    if numpy_result.is_checked_type:
        return numpy_result.coerced_value if numpy_result.is_coerced else value

    # Process sequences (tuple, list, set)
    sequence_result = _process_sequence_type(name, annotation, value, strict)
    if sequence_result.is_checked_type:
        return sequence_result.coerced_value if sequence_result.is_coerced else value

    # Process dictionaries
    dict_result = _process_dict_type(name, annotation, value, strict)
    if dict_result.is_checked_type:
        return dict_result.coerced_value if dict_result.is_coerced else value

    # Process union types
    if outer_type is UnionType:
        return _process_union_type(name, annotation, value, strict)

    # == Literal
    if outer_type is Literal:
        return _process_literal_type(name, annotation, value, strict)

    # ==== Raise error if the type is not handled
    raise ValueError(f"Parameter '{name}' does not have a supported type")


def _process_base_params_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process BaseParams types."""
    # avoid circular import
    from parametric import BaseParams

    try:
        if issubclass(annotation, BaseParams):
            if isinstance(value, BaseParams):
                return _ProcessingResult(True, False, None)
            else:
                raise ValueError(f"Parameter '{name}' must be a subclass of BaseParams")
    except TypeError:
        pass
    return _ProcessingResult(False, False, None)


def _process_numpy_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process numpy array types."""
    inner_types = get_args(annotation)

    if annotation is np.array or get_origin(annotation) is np.array:
        raise ValueError(f"Type of {name} cannot be 'np.array'. Try np.ndarray[int] instead")

    if annotation is np.ndarray:
        raise ValueError(
            f"Type of {name} cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])"
        )

    if get_origin(annotation) is not np.ndarray:
        return _ProcessingResult(False, False, None)

    if len(inner_types) != 1:
        raise ValueError(f"dtype of 'np.ndarray' {name} should have exactly 1 inner args (e.g. np.ndarray[int])")

    arr_dtype = inner_types[0]

    # Check for allowed numpy dtypes
    allowed_dtypes = {int, float, bool}
    allowed_dtypes.update(ALLOWED_NUMPY_TYPES)

    if arr_dtype not in allowed_dtypes:
        raise ValueError(
            f"dtype of 'np.ndarray' {name} must be one of the allowed types: "
            f"{', '.join(str(dtype.__name__) for dtype in allowed_dtypes)}"
        )

    return _ProcessingResult(True, True, np.asarray(value, dtype=inner_types[0]))


def _process_sequence_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process sequence types (tuple, list, set)."""
    outer_type = get_origin(annotation)
    inner_types = get_args(annotation)

    # Validate basic sequence requirements
    if outer_type not in {tuple, list, set}:
        return _ProcessingResult(False, False, None)

    # Validate sequence type annotation
    if outer_type in {tuple, list, set} and outer_type is None:
        raise ValueError(f"Type of {name} cannot be '{annotation.__name__}' without specifying element types")

    # Validate value type
    if not isinstance(value, (list, tuple, set, frozenset, GeneratorType, deque)):
        raise ValueError(f"In {name}, {type(value)} is not sequence compatible.")

    # Process based on sequence type
    if outer_type is tuple:
        result = _process_tuple_elements(name, value, inner_types, strict)
    else:  # list or set
        result = _process_list_or_set_elements(name, outer_type, value, inner_types, strict)

    return _ProcessingResult(True, True, result)


def _process_old_style_types(annotation: Type, outer_type: Type) -> None:
    """Check and raise errors for old style type hints."""
    try:
        if annotation._name == "Tuple":
            raise ValueError("Old Tuple[x,y,z] type is bad practice. Use tuple[x,y,z] instead.")
        if annotation._name == "Optional":
            raise ValueError("Old Optional[x] type is bad practice. Use x | None instead.")
    except AttributeError:
        # Handle case where annotation is not a class
        pass

    if outer_type is Union or annotation is Union:
        raise ValueError("Old Union[x,y,z] type is bad practice. Use x | y | z instead.")


def _process_union_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process union types."""
    inner_types = get_args(annotation)
    if get_origin(annotation) is not UnionType:
        return _ProcessingResult(False, False, None)

    type_presence = {
        "basic": False,
        "sequence": None,
    }

    SEQUENCE_TYPES = {tuple, list, set, np.ndarray}

    # Validate union type composition
    for arg in inner_types:
        outer_arg = get_origin(arg)
        if arg is type(None):
            continue
        if outer_arg in SEQUENCE_TYPES:
            if type_presence["sequence"]:
                raise ValueError("Union of multiple sequence types is bad practice")
            type_presence["sequence"] = outer_arg
        elif type_presence["basic"]:
            raise ValueError("Union of common types is bad practice")
        else:
            type_presence["basic"] = True

    # Try conversions
    conversion_errors = []
    for arg in inner_types:
        try:
            tmp_res = process_field(name, arg, value, strict=strict)
            return _ProcessingResult(True, True, tmp_res)
        except (TypeError, ValueError) as e:
            conversion_errors.append(str(e))

    error_details = "\n".join(f"- {err}" for err in conversion_errors)
    raise ValueError(f"Value '{value}' for '{name}' doesn't match any type in the union. Errors:\n{error_details}")


def _process_literal_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process literal types."""
    if get_origin(annotation) is not Literal:
        return _ProcessingResult(False, False, None)

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

    return _ProcessingResult(True, False, None)


def _process_dict_type(name: str, annotation: Type, value: Any, strict: bool) -> _ProcessingResult:
    """Process dictionary types."""
    outer_type = get_origin(annotation)
    if annotation is dict and outer_type is None:
        raise ValueError(
            f"Type of {name} cannot be 'dict' without specifying key and value types (e.g. dict[str, int])"
        )

    if outer_type is not dict:
        return _ProcessingResult(False, False, None)

    if not isinstance(value, dict):
        raise ValueError(f"In {name}, {type(value)} is not dict compatible.")

    inner_types = get_args(annotation)
    if len(inner_types) != 2:
        raise ValueError(f"dict type {name} must have exactly 2 type arguments (key and value types)")

    key_type, value_type = inner_types
    res = {}

    for k, v in value.items():
        key_res = process_field(f"{name} key", key_type, k, strict=strict)
        value_res = process_field(f"{name} value", value_type, v, strict=strict)

        if key_res is not None or value_res is not None:
            res[key_res if key_res is not None else k] = value_res if value_res is not None else v
        else:
            res[k] = v

    return _ProcessingResult(True, True, res)


# Helper functions for sequence processing
def _process_tuple_elements(name: str, value: Any, inner_types: tuple, strict: bool) -> tuple:
    """Helper function to process tuple elements."""
    is_variadic = inner_types[-1] is Ellipsis
    if is_variadic:
        if len(inner_types) != 2:
            raise ValueError(f"when using Ellipsis in {name}, only one inner type is allowed, e.g. tuple[int, ...]")
    elif len(inner_types) != len(value):
        raise ValueError(f"Expected in {name} a tuple of length {len(inner_types)}, got {len(value)}")

    return tuple(_process_sequence_elements(name, value, inner_types, strict, is_variadic=is_variadic))


def _process_list_or_set_elements(
    name: str, outer_type: Type, value: Any, inner_types: tuple, strict: bool
) -> list | set:
    """Helper function to process list and set elements."""
    if len(inner_types) > 2 or (len(inner_types) == 2 and inner_types[-1] is not Ellipsis):
        raise ValueError(
            f"{outer_type.__name__} type {name} must have exactly 1 type argument (e.g. {outer_type.__name__}[int])"
        )

    is_variadic = inner_types[-1] is Ellipsis or len(inner_types) == 1
    result = _process_sequence_elements(name, value, inner_types, strict, is_variadic=is_variadic)

    return list(result) if outer_type is list else set(result)


def _process_sequence_elements(name: str, value: Any, inner_types: tuple, strict: bool, *, is_variadic: bool) -> list:
    """Helper function to process individual sequence elements."""
    res = []
    for i, val_i in enumerate(value):
        curr_inner_type = inner_types[0] if is_variadic else inner_types[i]
        arg_res = process_field(name, curr_inner_type, val_i, strict=strict)
        res.append(arg_res if arg_res is not None else val_i)
    return res
