import enum
import os
from pathlib import Path
from typing import Any, get_type_hints

import numpy as np
import yaml

from parametric._helpers import ConversionFromType
from parametric._type_node import (
    BoolNode,
    BytesNode,
    EnumNode,
    FloatNode,
    IntNode,
    LiteralNode,
    NoneTypeNode,
    PathNode,
    StrNode,
)
from parametric._typehint_parsing import parse_typehint


class BaseParams:
    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

    def __init__(self):
        self._inner_params_that_are_baseparam_class: set[str] = set()

        # ==== convert all on init
        self._name_to_type_node = {
            name: parse_typehint(name, typehint) for name, typehint in self._get_all_type_hints().items()
        }
        self._default_values = {}
        for name in self._name_to_type_node:
            value = getattr(self, name)

            self._default_values |= self._convert_and_set(
                name, value, conversion_from_type=ConversionFromType.PYTHON_OBJECT
            )

        self._is_frozen = True

        # flag for finishing init for __setattr__
        self._is_init_finished = True

    @classmethod
    def _get_all_type_hints(cls) -> dict[str, Any]:
        hints: dict[str, Any] = {}
        # manually traverse the method resolution order (MRO) and collect type hints from all base classes.
        for base in reversed(cls.__mro__):
            if base is not object:  # Ignore the top-level object class
                hints.update(get_type_hints(base))
        return hints

    def _convert_and_set(self, name: str, value: Any, conversion_from_type: ConversionFromType) -> dict[str, Any]:
        try:
            if conversion_from_type == ConversionFromType.PYTHON_OBJECT:
                converted_val = self._name_to_type_node[name].from_python_object(value)
            elif conversion_from_type == ConversionFromType.DUMPABLE:
                converted_val = self._name_to_type_node[name].from_dumpable(value)
            elif conversion_from_type == ConversionFromType.STR:
                converted_val = self._name_to_type_node[name].from_str(value)
            else:
                raise Exception(f"unsupported conversion_from_type {conversion_from_type}")

            if isinstance(converted_val, BaseParams):
                self._inner_params_that_are_baseparam_class.add(name)
            else:
                self._inner_params_that_are_baseparam_class.discard(name)
        except Exception as e:
            raise AttributeError(f"Cannot convert '{name}': {e}")

        setattr(self, name, converted_val)
        return {name: converted_val}

    def override_from_dict(self, data: dict[str, Any]):
        self._override_from_dict(data, conversion_from_type=ConversionFromType.PYTHON_OBJECT)

    def _override_from_dict(self, data: dict[str, Any], conversion_from_type: ConversionFromType) -> None:
        self._set_freeze(False)

        override_dict = {}
        for name, value in data.items():
            if name not in self._name_to_type_node:
                raise RuntimeError(f"Parameter name '{name}' does not exist")

            override_dict |= self._convert_and_set(name, value, conversion_from_type)

        self._set_freeze(True)

    def _set_freeze(self, is_frozen: bool) -> None:
        for name in self._name_to_type_node:
            if name in self._inner_params_that_are_baseparam_class:
                base_params_instance: BaseParams = getattr(self, name)
                base_params_instance._set_freeze(is_frozen)

        self._is_frozen = is_frozen

    def model_dump_non_defaults(self):
        changed = {}
        for field_name, def_val in self._default_values.items():
            curr_val = getattr(self, field_name)
            if not self._is_equal_field(def_val, curr_val):
                changed[field_name] = curr_val
        return changed

    def override_from_cli(self) -> None:
        import argparse

        # Initialize the parser
        parser = argparse.ArgumentParser()

        # Add arguments
        for name, type_node in self._name_to_type_node.items():
            if isinstance(
                type_node,
                (
                    IntNode,
                    FloatNode,
                    StrNode,
                    BoolNode,
                    BytesNode,
                    PathNode,
                    NoneTypeNode,
                    LiteralNode,
                    EnumNode,
                ),
            ):
                parser.add_argument(f"--{name}", type=str, required=False)

        args = parser.parse_args()
        changed_params = {k: v for k, v in vars(args).items() if parser.get_default(k) != v}

        self._override_from_dict(changed_params, conversion_from_type=ConversionFromType.STR)

    def override_from_yaml_file(self, filepath: Path | str) -> None:
        filepath = Path(filepath)
        if not filepath.is_file():
            return

        with open(filepath) as f:
            changed_params = yaml.safe_load(f)
        if changed_params is None:
            return

        self._override_from_dict(changed_params, conversion_from_type=ConversionFromType.DUMPABLE)

    def override_from_envs(self, env_prefix: str = "_param_") -> None:
        # Build a dictionary mapping lowercase names to actual case-sensitive names
        lower_to_actual_case = {}
        for name in self._name_to_type_node:
            lower_name = name.lower()
            if lower_name in lower_to_actual_case:
                conflicting_name = lower_to_actual_case[lower_name]
                raise RuntimeError(
                    f"Parameter names '{name}' and '{conflicting_name}' conflict when considered in lowercase.",
                )
            lower_to_actual_case[lower_name] = name

        changed_params = {}
        for key, value in os.environ.items():
            if not key.lower().startswith(env_prefix):
                continue
            param_key = key[len(env_prefix) :].lower()

            if param_key in lower_to_actual_case:
                actual_name = lower_to_actual_case[param_key]
                changed_params[actual_name] = value

        self._override_from_dict(changed_params, conversion_from_type=ConversionFromType.STR)

    def to_dumpable_dict(self) -> dict[str, Any]:
        dumpable_dict_res = {}
        for name, type_node in self._name_to_type_node.items():
            val = getattr(self, name)
            if isinstance(val, BaseParams):
                dumpable_dict_res[name] = val.to_dumpable_dict()
            else:
                dumpable_dict_res[name] = type_node.to_dumpable(val)
        return dumpable_dict_res

    def save_yaml(self, filepath: str) -> None:
        with open(filepath, "w") as stream:
            yaml.dump(self.to_dumpable_dict(), stream)

    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self._name_to_type_node:
            if field_name not in other._name_to_type_node:
                return False
            if not self._is_equal_field(getattr(self, field_name), getattr(other, field_name)):
                return False
        return True

    def _is_equal_field(self, val1: Any, val2: Any) -> bool:
        # for enums
        if isinstance(val1, enum.Enum) and isinstance(val2, enum.Enum):
            return val1.value == val2.value
        # for np.ndarray
        if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
            return np.array_equal(val1, val2)
        # for all others
        if val1 == val2:
            return True
        return False

    def __setattr__(self, key: str, value: Any):
        # NOTE user defined vars are created before __init__, so self._is_init_finished doesn't exist
        # in this case we simply want to create this variable without any checks
        if getattr(self, "_is_init_finished", None) is None:
            super().__setattr__(key, value)
            return

        if key == "_is_frozen":
            super().__setattr__("_is_frozen", value)
            return

        if key not in self._name_to_type_node:
            raise AttributeError(f"Can't define parameter {key} after initialization")

        if self._is_frozen:
            raise AttributeError(f"Instance is frozen. Cannot modify attribute {key}")
        super().__setattr__(key, value)
