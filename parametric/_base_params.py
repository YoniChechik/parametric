import os
import sys
from pathlib import Path
from typing import Any

import yaml

from parametric._abstract_base_params import AbstractBaseParams
from parametric._gui.base import run_gui

EMPTY_PARAM = "__parametric_empty_field"


class BaseParams(AbstractBaseParams):
    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

    def _validate_immutable_typehints(self):
        for field_name, field_info in self.model_fields.items():
            if isinstance(field_info.annotation, type) and issubclass(field_info.annotation, BaseParams):
                inner_base_params: BaseParams = getattr(self, field_name)
                inner_base_params._validate_immutable_typehints()
            else:
                _validate_immutable_typehint(field_name, field_info.annotation)

    class Config:
        # validate after each assignment
        validate_assignment = True
        # to freeze later
        frozen = False
        # don't allow new fields after init
        extra = "forbid"
        # validate default values
        validate_default = True

    def override_from_dict(self, data: dict[str, Any]):
        for k, v in data.items():
            # NOTE: this also validates
            setattr(self, k, v)

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
        self.override_from_dict(yaml_data)

    def override_from_cli(self) -> None:
        import argparse

        # Initialize the parser
        parser = argparse.ArgumentParser()

        # Add arguments
        for field_name, field_info in self.model_fields.items():
            if isinstance(
                field_info.annotation,
                (type(int), type(float), type(bool), type(str), type(bytes), type(Path), type(None)),
            ):
                parser.add_argument(f"--{field_name}", type=field_info.annotation, required=False)

        args = parser.parse_args()
        changed_params = {k: v for k, v in vars(args).items() if parser.get_default(k) != v}

        self.override_from_dict(changed_params, is_strict=False)

    def override_from_envs(self, env_prefix: str = "_param_") -> None:
        # Build a dictionary mapping lowercase names to actual case-sensitive names
        lower_to_actual_case = {}
        for field_name in self.model_fields:
            lower_name = field_name.lower()
            if lower_name in lower_to_actual_case:
                conflicting_name = lower_to_actual_case[lower_name]
                raise RuntimeError(
                    f"Parameter names '{field_name}' and '{conflicting_name}' conflict when considered in lowercase.",
                )
            lower_to_actual_case[lower_name] = field_name

        changed_params = {}
        for key, value in os.environ.items():
            if not key.lower().startswith(env_prefix):
                continue
            param_key = key[len(env_prefix) :].lower()

            if param_key in lower_to_actual_case:
                actual_name = lower_to_actual_case[param_key]
                changed_params[actual_name] = value

        self.override_from_dict(changed_params, is_strict=False)

    def save_yaml(self, save_path: str | Path):
        with open(save_path, "w") as file:
            yaml.dump(self.model_dump_serializable(), file)

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

    def override_gui(self) -> None:
        """Launches a NiceGUI interface to override parameters interactively."""
        name_to_value = {name: self._get_value_including_empty(name) for name in self._name_to_type_node}
        override_dict = run_gui(self._name_to_type_node, name_to_value)

        self.override_from_dict(override_dict)
