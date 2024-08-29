import copy
import os
from pathlib import Path
from typing import Any, get_type_hints

import yaml

from parametric._abstract_base_params import AbstractBaseParams
from parametric._type_node import (
    BoolNode,
    BytesNode,
    EnumNode,
    LiteralNode,
    NoneTypeNode,
    NumberNode,
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
            name: parse_typehint(name, typehint) for name, typehint in get_type_hints(self).items()
        }
        self._default_values = {}
        for name in self._name_to_type_node:
            value = self._get_value_including_empty(name)

            # don't work on empty field
            if value == EMPTY_PARAM:
                continue

            self._default_values |= self._convert_and_set(name, value, is_strict=True)

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

    def _convert_and_set(self, name, value, is_strict: bool) -> dict[str, Any]:
        if is_strict:
            converted_val = self._name_to_type_node[name].cast_python_strict(value)
        else:
            converted_val = self._name_to_type_node[name].cast_python_relaxed(value)

        if isinstance(converted_val, BaseParams):
            self._inner_params_that_are_baseparam_class.add(name)
        else:
            self._inner_params_that_are_baseparam_class.discard(name)
        setattr(self, name, converted_val)
        return {name: converted_val}

    def _get_value_including_empty(self, field_name):
        given_value = getattr(self, field_name, EMPTY_PARAM)
        return given_value

    def override_from_dict(self, changed_params: dict[str, Any], is_strict: bool = True) -> dict[str, Any]:
        override_dict = {}
        for name, value in changed_params.items():
            if name not in self._name_to_type_node:
                raise RuntimeError(f"param name '{name}' does not exist")

            override_dict |= self._convert_and_set(name, value, is_strict)
        return override_dict

    def override_from_cli(self) -> dict[str, Any]:
        import argparse

        # Initialize the parser
        parser = argparse.ArgumentParser()

        # Add arguments
        for name, type_node in self._name_to_type_node.items():
            if isinstance(
                type_node, (NumberNode, StrNode, BoolNode, BytesNode, PathNode, NoneTypeNode, LiteralNode, EnumNode)
            ):
                parser.add_argument(f"--{name}", type=str, required=False, default=str(getattr(self, name)))

        args = parser.parse_args()
        changed_params = {k: v for k, v in vars(args).items() if parser.get_default(k) != v}

        return self.override_from_dict(changed_params, is_strict=False)

    def override_from_yaml(self, filepath: Path | str) -> dict[str, Any]:
        filepath = Path(filepath)
        if not filepath.is_file():
            return

        with open(filepath) as f:
            changed_params = yaml.safe_load(f)
        if changed_params is None:
            return

        return self.override_from_dict(changed_params, is_strict=False)

    def override_from_envs(self, env_prefix: str = "_param_") -> dict[str, Any]:
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

        return self.override_from_dict(changed_params, is_strict=False)

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
                dumpable_dict_res[name] = type_node.cast_dumpable(val)
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
        # NOTE: in the init phase _is_frozen is not yet declared, but setattr is called when we make new vars, so we default to False here
        if getattr(self, "_is_frozen", False):
            raise AttributeError(f"Params are frozen. Cannot modify attribute {key}")
        super().__setattr__(key, value)
