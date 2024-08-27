from abc import ABC, abstractmethod
from enum import EnumMeta
from pathlib import Path
from typing import Any, TypeVar

from parametric._abstract_base_params import AbstractBaseParams


class TypeCoercionError(Exception):
    def __init__(self, message: str = "Type coercion error"):
        super().__init__(message)


class TypeNode(ABC):
    def __init__(self, type_base_name: str) -> None:
        self.type_base_name = type_base_name

    def __repr__(self) -> str:
        return self.type_base_name

    @abstractmethod
    def _cast_python(self, value: Any, is_strict: bool) -> Any:
        pass

    def cast_python_strict(self, value: Any) -> Any:
        return self._cast_python(value, is_strict=True)

    def cast_python_relaxed(self, value: Any) -> Any:
        return self._cast_python(value, is_strict=False)

    def cast_dumpable(self, value: Any) -> Any:
        return self.cast_python_strict(value)


class StrNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("str")

    def _cast_python(self, value: Any, is_strict: bool) -> str:
        if isinstance(value, str):
            return value
        if is_strict:
            raise TypeCoercionError()
        return str(value)


class BoolNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("bool")

    def _cast_python(self, value: Any, is_strict: bool) -> bool:
        if isinstance(value, bool):
            return value
        if is_strict:
            raise TypeCoercionError()

        if isinstance(value, str):
            if value.lower().strip() in {"0", "-1", "off", "f", "false", "n", "no"}:
                return False
            elif value.lower().strip() in {"1", "on", "t", "true", "y", "yes"}:
                return True
        if isinstance(value, (int, float)):
            if value == 0 or value == -1:
                return False
            elif value == 1:
                return True
        raise TypeCoercionError()


class BytesNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("bytes")

    def _cast_python(self, value: Any, is_strict: bool) -> bytes:
        if isinstance(value, bytes):
            return value
        if is_strict:
            raise TypeCoercionError()

        return bytes(value)

    def cast_dumpable(self, value: Any) -> str:
        return str(self.cast_python_strict(value))


class PathNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("Path")

    def _cast_python(self, value: Any, is_strict: bool) -> Path:
        if isinstance(value, Path):
            return value
        if is_strict:
            raise TypeCoercionError()

        return Path(value)

    def cast_dumpable(self, value: Any) -> str:
        return str(self.cast_python_strict(value))


class NoneTypeNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("NoneType")

    def _cast_python(self, value: Any, is_strict: bool) -> None:
        if value is None:
            return None
        raise TypeCoercionError("Value is not None")


class BaseParamsNode(TypeNode):
    def __init__(self, base_params_type: AbstractBaseParams) -> None:
        super().__init__("BaseParams")
        self.base_params_type = base_params_type

    def _cast_python(self, value: Any, is_strict: bool):
        if isinstance(value, self.base_params_type):
            return value
        if is_strict:
            raise TypeCoercionError()

        if isinstance(value, dict):
            instance: AbstractBaseParams = self.base_params_type()
            instance.override_from_dict(value)
            return value

        raise TypeCoercionError(f"Cannot convert {value} to {self.base_params_type} (derived BaseParams)")

    def __repr__(self) -> str:
        return f"{self.base_params_type.__name__}(BaseParams)"

    def cast_dumpable(self, value: Any) -> dict:
        raise Exception("Can't cast dumpable")


class LiteralNode(TypeNode):
    def __init__(self, literal_args: tuple) -> None:
        super().__init__("Literal")
        self.literal_args = literal_args

    def _cast_python(self, value: Any, is_strict: bool):
        if value not in self.literal_args:
            raise TypeCoercionError(f"Value {value} is not a valid Literal")

        return value

    def __repr__(self) -> str:
        return f"Literal[{self.literal_args}]"


class EnumNode(TypeNode):
    def __init__(self, enum_type: EnumMeta) -> None:
        super().__init__("Enum")
        self.enum_type = enum_type

    def _cast_python(self, value: Any, is_strict: bool):
        return self.enum_type(value)

    def __repr__(self) -> str:
        return f"{self.enum_type.__name__}(Enum)"


# ========= number node
T = TypeVar("T")


class NumberNode(TypeNode):
    def __init__(self, type_base_name: str, conversion_function: T) -> None:
        super().__init__(type_base_name)
        self.conversion_function = conversion_function

    def _cast_python(self, value: Any, is_strict: bool) -> T:
        if isinstance(value, self.conversion_function):
            return value
        if is_strict:
            raise TypeCoercionError()

        # check for precision loss
        number_coercion_res = self.conversion_function(value)
        complex_coercion_res = complex(value)
        if complex_coercion_res != number_coercion_res:
            raise TypeCoercionError()

        return number_coercion_res


class IntNode(NumberNode):
    def __init__(self) -> None:
        super().__init__("int", int)


class FloatNode(NumberNode):
    def __init__(self) -> None:
        super().__init__("float", float)


class ComplexNode(NumberNode):
    def __init__(self) -> None:
        super().__init__("complex", complex)


# =========== CompoundTypeNode
class CompoundTypeNode(TypeNode):
    def __init__(self, type_base_name: str, inner_args: list[TypeNode]) -> None:
        super().__init__(type_base_name)
        self.inner_args = inner_args

    def __repr__(self) -> str:
        inner_repr = ", ".join(repr(inner) for inner in self.inner_args)
        return f"{self.type_base_name}[{inner_repr}]"


class TupleNode(CompoundTypeNode):
    def __init__(self, inner_args: list[TypeNode], is_ends_with_ellipsis: bool = False) -> None:
        super().__init__("Tuple", inner_args)
        self.is_any_length = is_ends_with_ellipsis | len(inner_args) == 1

    def _cast_python(self, value: Any, is_strict: bool) -> tuple:
        if is_strict and not isinstance(value, tuple):
            raise TypeCoercionError()

        converted_values = []
        for i, v in enumerate(value):
            if self.is_any_length:
                i = 0
            res = self.inner_args[i]._cast_python(v, is_strict)

            converted_values.append(res)

        return tuple(converted_values)

    def cast_dumpable(self, value: Any) -> list:
        return list(self.cast_python_strict(value))


_precedence_list = [
    IntNode,
    FloatNode,
    ComplexNode,
    NoneTypeNode,
    TupleNode,
    StrNode,
    PathNode,
]
_precedence = {type_node: i for i, type_node in enumerate(_precedence_list)}


class UnionNode(CompoundTypeNode):
    def __init__(self, inner_args: list[TypeNode]) -> None:
        super().__init__("Union", inner_args)
        self._check_invalid_combinations()

        self.sorted_inner_args: list[TypeNode] = sorted(self.inner_args, key=lambda x: _precedence[type(x)])

    def _check_invalid_combinations(self) -> None:
        str_present = any(isinstance(inner_type, StrNode) for inner_type in self.inner_args)
        path_present = any(isinstance(inner_type, PathNode) for inner_type in self.inner_args)

        if str_present and path_present:
            raise TypeError("Union with both `str` and `pathlib.Path` is not allowed.")

    def _cast_python(self, value: Any, is_strict: bool):
        for inner_type in self.sorted_inner_args:
            try:
                return inner_type._cast_python(value, is_strict)
            except Exception:
                continue
        raise TypeCoercionError()
