import os
import sys
from pathlib import Path
from typing import Any, get_type_hints

import yaml

from parametric._abstract_base_params import AbstractBaseParams
from parametric._typehint_parsing import parse_typehint

EMPTY_PARAM = "__parametric_empty_field"


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
        for name in self._name_to_type_node:
            value = self._get_value_including_empty(name)

            # don't work on empty field
            if value == EMPTY_PARAM:
                continue

            self._convert_and_set(name, value, is_strict=True)

    def _convert_and_set(self, name, value, is_strict: bool):
        if is_strict:
            conversion_return = self._name_to_type_node[name].cast_python_strict(value)
        else:
            conversion_return = self._name_to_type_node[name].cast_python_relaxed(value)

        if isinstance(conversion_return, BaseParams):
            self._inner_params_that_are_baseparam_class.add(name)
        else:
            self._inner_params_that_are_baseparam_class.discard(name)
        setattr(self, name, conversion_return)

    def _get_value_including_empty(self, field_name):
        given_value = getattr(self, field_name, EMPTY_PARAM)
        return given_value

    def override_from_dict(self, changed_params: dict[str, Any], is_strict: bool = True) -> None:
        for name, value in changed_params.items():
            if name not in self._name_to_type_node:
                raise RuntimeError(f"param name '{name}' does not exist")

            self._convert_and_set(name, value, is_strict)

    def override_from_cli(self):
        argv = sys.argv[1:]  # Skip the script name
        if len(argv) % 2 != 0:
            raise RuntimeError(
                "Got odd amount of space separated strings as CLI inputs. Must be even as '--key value' pairs",
            )
        changed_params = {}
        for i in range(0, len(argv), 2):
            key = argv[i]
            if not key.startswith("--"):
                raise RuntimeError(f"Invalid argument key: {key}. Argument keys must start with '--'.")
            key = key.lstrip("-")
            value = argv[i + 1]
            changed_params[key] = value

        self.override_from_dict(changed_params, is_strict=False)

    def override_from_yaml(self, filepath: Path | str) -> None:
        filepath = Path(filepath)
        if not filepath.is_file():
            return

        with open(filepath) as f:
            changed_params = yaml.safe_load(f)
        if changed_params is None:
            return

        self.override_from_dict(changed_params, is_strict=False)

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

        self.override_from_dict(changed_params, is_strict=False)

    def to_dict(self) -> dict[str, Any]:
        if not self._is_frozen:
            raise RuntimeError("'to_dict' only works on frozen params. please run freeze() first")
        res_dict = {}
        for field_name in self._name_to_type_node:
            value = getattr(self, field_name)
            if isinstance(value, BaseParams):
                value = value.to_dict()
            res_dict[field_name] = value
        return res_dict

    def _to_dumpable_dict(self) -> dict[str, Any]:
        dumpable_dict_res = {}
        for name, type_node in self._name_to_type_node.items():
            val = getattr(self, name)
            if isinstance(val, BaseParams):
                dumpable_dict_res[name] = val._to_dumpable_dict()
            else:
                dumpable_dict_res[name] = type_node.cast_dumpable(val)
        return dumpable_dict_res

    def save_yaml(self, filepath: str) -> None:
        if not self._is_frozen:
            raise RuntimeError("'save_yaml' only works on frozen params. please run freeze() first")

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
