from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import EnumType
from pathlib import Path
from typing import Any


@dataclass
class ConversionReturn:
    converted_value: Any
    is_coerced: bool


class TypeNode(ABC):
    def __init__(self, type_base_name: str) -> None:
        self.type_base_name = type_base_name

    def __repr__(self) -> str:
        return self.type_base_name

    @abstractmethod
    def convert(self, value: Any) -> ConversionReturn:
        pass


class IntNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("int")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, int):
            return ConversionReturn(value, False)
        return ConversionReturn(int(value), True)


class FloatNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("float")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, float):
            return ConversionReturn(value, False)
        return ConversionReturn(float(value), True)


class ComplexNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("complex")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, complex):
            return ConversionReturn(value, False)
        return ConversionReturn(complex(value), True)


class StrNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("str")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, str):
            return ConversionReturn(value, False)
        return ConversionReturn(str(value), True)


class BoolNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("bool")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, bool):
            return ConversionReturn(value, False)
        return ConversionReturn(bool(value), True)


class BytesNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("bytes")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, bytes):
            return ConversionReturn(value, False)
        return ConversionReturn(bytes(value), True)


class PathNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("Path")

    def convert(self, value: Any) -> ConversionReturn:
        if isinstance(value, Path):
            return ConversionReturn(value, False)
        return ConversionReturn(Path(value), True)


class NoneTypeNode(TypeNode):
    def __init__(self) -> None:
        super().__init__("NoneType")

    def convert(self, value: Any) -> ConversionReturn:
        if value is None:
            return ConversionReturn(None, False)
        raise ValueError("Value is not None")


class BaseParamsNode(TypeNode):
    def __init__(self, base_params_type: Any) -> None:
        super().__init__("BaseParams")
        self.base_params_type = base_params_type

    def convert(self, value: Any) -> ConversionReturn:
        # this import is here to avoid circular imports
        from parametric._base_params import BaseParams

        if isinstance(value, self.base_params_type):
            return ConversionReturn(value, False)

        if isinstance(value, dict):
            instance: BaseParams = self.base_params_type()
            instance.override_from_dict(value)
            return ConversionReturn(value, True)

        raise ValueError(f"Cannot convert {value} to {self.base_params_type} (derived BaseParams)")

    def __repr__(self) -> str:
        return f"{self.base_params_type.__name__}(BaseParams)"


# ================ multi choice
class MultiChoiceTypeNode(TypeNode):
    def __init__(self, type_base_name: str) -> None:
        super().__init__(type_base_name)
        self.chosen_ind: int = -1


class LiteralNode(MultiChoiceTypeNode):
    def __init__(self, literal_args: tuple) -> None:
        super().__init__("Literal")
        self.literal_args = literal_args

    def convert(self, value: Any) -> ConversionReturn:
        if value not in self.literal_args:
            raise ValueError(f"Value {value} is not a valid Literal")

        self.chosen_ind = self.literal_args.index(value)
        return ConversionReturn(value, False)

    def __repr__(self) -> str:
        return f"Literal[{self.literal_args}]"


class EnumNode(MultiChoiceTypeNode):
    def __init__(self, enum_type: EnumType) -> None:
        super().__init__("Enum")
        self.enum_type = enum_type

    def convert(self, value: Any) -> ConversionReturn:
        try:
            converted_val = self.enum_type(value)
        except ValueError:
            raise ValueError(f"Value {value} is not a valid {self.enum_type.__name__}")

        self.chosen_ind = tuple(self.enum_type).index(converted_val)

        return ConversionReturn(converted_val, False)

    def __repr__(self) -> str:
        return f"{self.enum_type.__name__}(Enum)"


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
        self.is_ends_with_ellipsis = is_ends_with_ellipsis

    def convert(self, value: Any) -> ConversionReturn:
        converted_values = []
        is_coerced = not (isinstance(value, tuple))
        for i, v in enumerate(value):
            if self.is_ends_with_ellipsis:
                i = 0
            res = self.inner_args[i].convert(v)

            converted_values.append(res.converted_value)
            is_coerced |= res.is_coerced

        return ConversionReturn(tuple(converted_values), is_coerced)


class UnionNode(CompoundTypeNode, MultiChoiceTypeNode):
    def __init__(self, inner_args: list[TypeNode]) -> None:
        MultiChoiceTypeNode.__init__(self, "Union")  # Initialize MultiChoiceTypeNode part
        CompoundTypeNode.__init__(self, "Union", inner_args)  # Initialize CompoundTypeNode part

    def convert(self, value: Any) -> ConversionReturn:
        """Handles conversion for Union types."""

        best_conversion_return: ConversionReturn | None = None

        for i, inner_type in enumerate(self.inner_args):
            try:
                conversion_return = inner_type.convert(value)
                # This is the best possible solution because it wasn't coerced. we can stop looking
                if not conversion_return.is_coerced:
                    self.chosen_ind = i
                    return conversion_return
                # second best because it is coerced - keep looking in case we get to not coerced solution
                if best_conversion_return is None:
                    self.chosen_ind = i
                    best_conversion_return = conversion_return
            except Exception:
                continue

        if best_conversion_return is not None:
            return best_conversion_return
        raise ValueError(f"Cannot convert {value} to anything")
