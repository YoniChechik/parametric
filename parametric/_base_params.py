import os
import sys
from pathlib import Path, PurePath
from typing import Any, get_type_hints

import yaml

from parametric._const import EMPTY_PARAM
from parametric._wrangle_type import wrangle_type


class BaseParams:
    def __init__(self):
        self._is_frozen = False
        self._inner_params_that_are_baseparam_class: set[str] = set()

        # ==== convert all on init
        param_name_to_type_hint = get_type_hints(self)
        for param_name, field_type in param_name_to_type_hint.items():
            value = self._get_value_including_empty(param_name)

            # don't work on empty field
            if value == EMPTY_PARAM:
                continue

            self._wrangle_and_set(param_name, field_type, value)

    def _wrangle_and_set(self, param_name, field_type, value):
        wrangle_type_return = wrangle_type(param_name, value, field_type)
        if isinstance(wrangle_type_return.converted_value, BaseParams):
            self._inner_params_that_are_baseparam_class.add(param_name)
        else:
            self._inner_params_that_are_baseparam_class.discard(param_name)
        setattr(self, param_name, wrangle_type_return.converted_value)

    def _get_value_including_empty(self, field_name):
        given_value = getattr(self, field_name, EMPTY_PARAM)
        return given_value

    def override_from_dict(self, changed_params: dict[str, Any]):
        param_name_to_type_hint = get_type_hints(self)
        for param_name, value in changed_params.items():
            if param_name not in param_name_to_type_hint:
                raise RuntimeError(f"param name {param_name} does not exist")

            field_type = param_name_to_type_hint[param_name]
            self._wrangle_and_set(param_name, field_type, value)

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

        self.override_from_dict(changed_params)

    def override_from_yaml(self, filepath: Path | str) -> None:
        filepath = Path(filepath)
        if not filepath.is_file():
            return

        with open(filepath) as f:
            changed_params = yaml.safe_load(f)
        if changed_params is None:
            return

        self.override_from_dict(changed_params)

    def override_from_envs(self, env_prefix: str = "_param_") -> None:
        param_name_to_type_hint = get_type_hints(self)

        # Build a dictionary mapping lowercase names to actual case-sensitive names
        lower_to_actual_case = {}
        for param_name in param_name_to_type_hint:
            lower_name = param_name.lower()
            if lower_name in lower_to_actual_case:
                conflicting_name = lower_to_actual_case[lower_name]
                raise RuntimeError(
                    f"Parameter names '{param_name}' and '{conflicting_name}' conflict when considered in lowercase.",
                )
            lower_to_actual_case[lower_name] = param_name

        changed_params = {}
        for key, value in os.environ.items():
            if not key.lower().startswith(env_prefix):
                continue
            param_key = key[len(env_prefix) :].lower()

            if param_key in lower_to_actual_case:
                actual_param_name = lower_to_actual_case[param_key]
                changed_params[actual_param_name] = value

        self.override_from_dict(changed_params)

    def to_dict(self) -> dict[str, Any]:
        if not self._is_frozen:
            raise RuntimeError("'to_dict' only works on frozen params. please run freeze() first")
        param_name_to_type_hint = get_type_hints(self)
        res_dict = {}
        for field_name in param_name_to_type_hint:
            value = getattr(self, field_name)
            if isinstance(value, BaseParams):
                value = value.to_dict()
            res_dict[field_name] = value
        return res_dict

    def save_yaml(self, filepath: str) -> None:
        if not self._is_frozen:
            raise RuntimeError("'save_yaml' only works on frozen params. please run freeze() first")

        # ==== Custom representers
        # make your own patched dumper type and use it explicitly, so you won't modify the global mutable state of PyYAML itself
        class CustomDumper(yaml.SafeDumper):
            pass

        # avoid `!!python/tuple` for every tuple by converting to list
        def tuple_to_list_representer(dumper: yaml.SafeDumper, data):
            return dumper.represent_list(list(data))

        # avoid `!!python/object/apply:pathlib...` for every Path by converting to str
        def path_to_str_representer(dumper: yaml.SafeDumper, data):
            return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))

        # Register the custom representer with PyYAML
        CustomDumper.add_representer(tuple, tuple_to_list_representer)
        CustomDumper.add_multi_representer(PurePath, path_to_str_representer)

        with open(filepath, "w") as stream:
            stream.write(yaml.dump(self.to_dict(), Dumper=CustomDumper))

    def freeze(self) -> None:
        param_name_to_type_hint = get_type_hints(self)
        for param_name in param_name_to_type_hint:
            # check empty field
            if self._get_value_including_empty(param_name) == EMPTY_PARAM:
                raise ValueError(f"{param_name} is empty and must be set before freeze()")
            if param_name in self._inner_params_that_are_baseparam_class:
                getattr(self, param_name).freeze()

        self._is_frozen = True

    def __setattr__(self, key, value):
        # NOTE: in the init phase _is_frozen is not yet declared, but setattr is called when we make new vars, so we default to False here
        if getattr(self, "_is_frozen", False):
            raise AttributeError(f"Params are frozen. Cannot modify attribute {key}")
        super().__setattr__(key, value)
