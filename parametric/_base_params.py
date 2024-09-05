import copy
import os
from pathlib import Path
from typing import Any, get_type_hints

import yaml

from parametric._helpers import AbstractBaseParams, ConversionFromType
from parametric._type_node import (
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
)
from parametric._typehint_parsing import parse_typehint

EMPTY_PARAM = "___parametric_empty_field"


class BaseParams(AbstractBaseParams):
    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

    def __init__(self):
        self._is_frozen = False
        self._inner_params_that_are_baseparam_class: set[str] = set()

        # ==== convert all on init
        self._name_to_type_node = {
            name: parse_typehint(name, typehint) for name, typehint in self._get_all_type_hints().items()
        }
        self._default_values = {}
        for name in self._name_to_type_node:
            value = self._get_value_including_empty(name)

            # don't work on empty field
            if value == EMPTY_PARAM:
                continue

            self._default_values |= self._convert_and_set(
                name, value, conversion_from_type=ConversionFromType.PYTHON_OBJECT
            )

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

    def get_defaults_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._default_values)

    def get_overrides_dict(self) -> dict[str, Any]:
        res_dict = self.to_dict()
        overrides_dict = {}
        for name in self._name_to_type_node:
            if name not in self._default_values and name in res_dict:
                overrides_dict[name] = res_dict[name]
            if res_dict[name] != self._default_values[name]:
                overrides_dict[name] = res_dict[name]
        return copy.deepcopy(overrides_dict)

    def _convert_and_set(self, name, value, conversion_from_type: ConversionFromType) -> dict[str, Any]:
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
        setattr(self, name, converted_val)
        return {name: converted_val}

    def _get_value_including_empty(self, field_name):
        given_value = getattr(self, field_name, EMPTY_PARAM)
        return given_value

    def _override_from_dict(self, changed_params: dict[str, Any], conversion_from_type: ConversionFromType) -> None:
        override_dict = {}
        for name, value in changed_params.items():
            if name not in self._name_to_type_node:
                raise RuntimeError(f"param name '{name}' does not exist")

            override_dict |= self._convert_and_set(name, value, conversion_from_type)

    def override_from_dict(self, changed_params: dict[str, Any]) -> None:
        self._override_from_dict(changed_params, conversion_from_type=ConversionFromType.PYTHON_OBJECT)

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
                    ComplexNode,
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

    def override_from_yaml(self, filepath: Path | str) -> None:
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

    def to_dict(self) -> dict[str, Any]:
        res_dict = {}
        for field_name in self._name_to_type_node:
            value = self._get_value_including_empty(field_name)
            if value == EMPTY_PARAM:
                continue
            if isinstance(value, BaseParams):
                value = value.to_dict()
            res_dict[field_name] = value
        return res_dict

    def _to_dumpable_dict(self) -> dict[str, Any]:
        dumpable_dict_res = {}
        for name, type_node in self._name_to_type_node.items():
            val = self._get_value_including_empty(name)
            if val == EMPTY_PARAM:
                continue
            if isinstance(val, BaseParams):
                dumpable_dict_res[name] = val._to_dumpable_dict()
            else:
                dumpable_dict_res[name] = type_node.to_dumpable(val)
        return dumpable_dict_res

    def save_yaml(self, filepath: str) -> None:
        with open(filepath, "w") as stream:
            yaml.dump(self._to_dumpable_dict(), stream)

    def freeze(self) -> None:
        for name in self._name_to_type_node:
            # check empty field
            if self._get_value_including_empty(name) == EMPTY_PARAM:
                raise ValueError(f"{name} is empty and must be set before freeze()")
            if name in self._inner_params_that_are_baseparam_class:
                base_params_instance: BaseParams = getattr(self, name)
                base_params_instance.freeze()

        self._is_frozen = True

    def __setattr__(self, key, value):
        # user defined vars are created before __init__, so self._is_init_finished doesn't exist
        # in this case we simply want to create this variable without any checks
        if getattr(self, "_is_init_finished", None) is None:
            super().__setattr__(key, value)
            return

        if (key not in self._name_to_type_node) and (key != "_is_frozen"):
            raise AttributeError(f"Can't set undefined parameter {key}")

        if self._is_frozen:
            raise AttributeError(f"Params are frozen. Cannot modify attribute {key}")
        super().__setattr__(key, value)

    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self._name_to_type_node:
            value1 = self._get_value_including_empty(field_name)
            value2 = other._get_value_including_empty(field_name)
            if value1 != value2:
                return False
        return True
