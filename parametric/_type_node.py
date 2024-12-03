from enum import Enum, EnumMeta
from pathlib import Path
from typing import Any, Generic, Literal, Tuple, TypeVar, Union

import numpy as np

from parametric._helpers import ConversionFromType


class TypeCoercionError(Exception):
    def __init__(self, message: str = "Type coercion error"):
        super().__init__(message)


T = TypeVar("T")


class TypeNode(Generic[T]):
    def __init__(self, type: Any) -> None:
        self.type = type

    def __repr__(self) -> str:
        return self.type.__name__

    def from_python_object(self, value: Any) -> T:
        if isinstance(value, self.type):
            return value
        raise TypeCoercionError()

    def from_dumpable(self, value: Any) -> T:
        return self.from_python_object(value)

    def from_str(self, value: str) -> T:
        if not isinstance(value, str):
            raise TypeCoercionError()
        return self.from_dumpable(value)

    def to_dumpable(self, value: T) -> Any:
        if isinstance(value, self.type):
            return value
        raise TypeCoercionError()


class NumpyNode(TypeNode[np.ndarray]):
    def __init__(self, inner_arg: TypeNode) -> None:
        super().__init__(np.ndarray)
        self._inner_arg = inner_arg

    def __repr__(self) -> str:
        return f"{self.type.__name__}[{self._inner_arg}]"

    def from_python_object(self, value: Any) -> T:
        try:
            arr = np.array(value, dtype=self._inner_arg.type)
            arr.flags.writeable = False
            return arr

        except Exception:
            raise TypeCoercionError()

    def to_dumpable(self, value: np.ndarray) -> list:
        return value.tolist()


class IntNode(TypeNode[int]):
    def __init__(self) -> None:
        super().__init__(int)

    def from_str(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeCoercionError()
        return int(value)


class FloatNode(TypeNode[float]):
    def __init__(self) -> None:
        super().__init__(float)

    def from_python_object(self, value: float) -> float:
        if isinstance(value, float) or isinstance(value, int):
            return float(value)
        raise TypeCoercionError()

    def from_str(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeCoercionError()
        return float(value)


class StrNode(TypeNode[str]):
    def __init__(self) -> None:
        super().__init__(str)

    def from_str(self, value: str) -> str:
        if not isinstance(value, str):
            raise TypeCoercionError()
        return str(value)


class BoolNode(TypeNode[bool]):
    def __init__(self) -> None:
        super().__init__(bool)

    def from_str(self, value: str) -> bool:
        if not isinstance(value, str):
            raise TypeCoercionError()
        if value.lower().strip() in {"0", "-1", "off", "f", "false", "n", "no"}:
            return False
        elif value.lower().strip() in {"1", "on", "t", "true", "y", "yes"}:
            return True
        raise TypeCoercionError()


class BytesNode(TypeNode[bytes]):
    def __init__(self) -> None:
        super().__init__(bytes)

    def from_dumpable(self, value: Any) -> bytes:
        if isinstance(value, str):
            return value.encode("utf-8")
        raise TypeCoercionError()

    def to_dumpable(self, value: bytes) -> str:
        return self.from_python_object(value).decode("utf-8")


class PathNode(TypeNode[Path]):
    def __init__(self) -> None:
        super().__init__(Path)

    def from_dumpable(self, value: Any) -> Path:
        return Path(value)

    def to_dumpable(self, value: Path) -> str:
        return str(value.as_posix())


class NoneTypeNode(TypeNode[None]):
    def __init__(self) -> None:
        super().__init__(type(None))

    def from_str(self, value: str) -> None:
        if value.lower().strip() in {"none", "null"}:
            return None
        raise TypeCoercionError("Value is not None")


class BaseParamsNode(TypeNode):
    def __init__(self, base_params_type) -> None:
        from parametric._base_params import BaseParams

        super().__init__(BaseParams)
        self.base_params_type: BaseParams = base_params_type

    def __repr__(self) -> str:
        return f"{self.base_params_type.__name__}(BaseParams)"

    def from_python_object(self, value: Any):
        from parametric._base_params import BaseParams

        if isinstance(value, self.base_params_type):
            value: BaseParams
            return value
        raise TypeCoercionError()

    def from_dumpable(self, value: dict[str, Any]):
        from parametric._base_params import BaseParams

        if isinstance(value, dict):
            instance: BaseParams = self.base_params_type()
            instance._override_from_dict(value, conversion_from_type=ConversionFromType.DUMPABLE)
            return instance

        raise TypeCoercionError(f"Cannot convert {value} to {self.base_params_type} (derived BaseParams)")

    def to_dumpable(self, value) -> dict:
        raise Exception("Can't cast dumpable")


class LiteralNode(TypeNode[Any]):
    def __init__(self, literal_args: tuple) -> None:
        super().__init__(Literal)
        self.literal_args = literal_args

    def from_python_object(self, value: Any):
        if value not in self.literal_args:
            raise TypeCoercionError(f"Value {value} is not a valid Literal")

        return value

    def __repr__(self) -> str:
        return f"Literal[{self.literal_args}]"

    def to_dumpable(self, value: Any) -> Any:
        return value


class EnumNode(TypeNode[Any]):
    def __init__(self, enum_type: EnumMeta) -> None:
        super().__init__(Enum)
        self.enum_type = enum_type

    def from_python_object(self, value: Any):
        return self.enum_type(value)

    def to_dumpable(self, value: Enum) -> str:
        return value.value

    def __repr__(self) -> str:
        return f"{self.enum_type.__name__}(Enum)"


# =========== CompoundTypeNode
class CompoundTypeNode(TypeNode):
    def __init__(self, type_base_name: str, inner_args: list[TypeNode]) -> None:
        super().__init__(type_base_name)
        self.inner_args = inner_args

    def __repr__(self) -> str:
        inner_repr = ", ".join(repr(inner) for inner in self.inner_args)
        return f"{self.type}[{inner_repr}]"


class TupleNode(CompoundTypeNode):
    def __init__(self, inner_args: list[TypeNode], is_ends_with_ellipsis: bool = False) -> None:
        super().__init__(Tuple, inner_args)
        self.is_any_length = is_ends_with_ellipsis | len(inner_args) == 1

    def _cast_prolog(self, value: Any) -> list[tuple[TypeNode, Any]]:
        res = []
        for i, v in enumerate(value):
            if self.is_any_length:
                i = 0
            res.append((self.inner_args[i], v))
        return res

    def from_python_object(self, value: Any) -> tuple:
        if not isinstance(value, tuple):
            raise TypeCoercionError()

        converted_values = []
        for node, v in self._cast_prolog(value):
            res = node.from_python_object(v)

            converted_values.append(res)

        return tuple(converted_values)

    def from_dumpable(self, value: Any) -> Any:
        converted_values = []
        for node, v in self._cast_prolog(value):
            res = node.from_dumpable(v)

            converted_values.append(res)

        return tuple(converted_values)

    def from_str(self, value: str) -> Any:
        if not isinstance(value, str):
            raise TypeCoercionError()

        converted_values = []
        for node, v in self._cast_prolog(value):
            res = node.from_str(v)

            converted_values.append(res)

        return tuple(converted_values)

    def to_dumpable(self, value: tuple) -> list:
        return list(node.to_dumpable(v) for node, v in self._cast_prolog(value))


_precedence_list_high_to_low = [
    EnumNode,
    LiteralNode,
    BoolNode,
    IntNode,
    FloatNode,
    NoneTypeNode,
    NumpyNode,
    TupleNode,
    BytesNode,
    PathNode,
    StrNode,
    BaseParamsNode,
]
_precedence = {type_node: i for i, type_node in enumerate(_precedence_list_high_to_low)}


class UnionNode(CompoundTypeNode):
    def __init__(self, inner_args: list[TypeNode]) -> None:
        super().__init__(Union, inner_args)

        self.sorted_inner_args: list[TypeNode] = sorted(self.inner_args, key=lambda x: _precedence[type(x)])

    def from_python_object(self, value: Any):
        for inner_type in self.sorted_inner_args:
            try:
                return inner_type.from_python_object(value)
            except Exception:
                continue
        raise TypeCoercionError()

    def from_dumpable(self, value: Any):
        for inner_type in self.sorted_inner_args:
            try:
                return inner_type.from_dumpable(value)
            except Exception:
                continue
        raise TypeCoercionError()

    def from_str(self, value: Any):
        if not isinstance(value, str):
            raise TypeCoercionError()

        for inner_type in self.sorted_inner_args:
            try:
                return inner_type.from_str(value)
            except Exception:
                continue
        raise TypeCoercionError()

    def to_dumpable(self, value: Any):
        for inner_type in self.sorted_inner_args:
            try:
                return inner_type.to_dumpable(value)
            except Exception:
                continue
        raise TypeCoercionError()
