import os
import sys
from pathlib import Path
from types import UnionType
from typing import Any, Tuple, Union, get_args, get_origin, get_type_hints

import yaml

# Immutable types set
BASE_TYPES = (int, float, bool, str, bytes, complex, Path)

EMPTY_FIELD = "__parametric_empty_field"


def _wrangle_type(field_name: str, value: Any, target_type: Any) -> Any:
    if target_type == Any:
        raise ValueError(f"Type `Any` is not allowed, cannot convert '{field_name}'")

    origin_type = get_origin(target_type)
    if origin_type in {Union, UnionType}:
        # Test that at least one conversion works
        for inner_type in get_args(target_type):
            try:
                return _wrangle_type(field_name, value, inner_type)
            except (ValueError, TypeError):
                continue
        raise ValueError(f"Cannot convert {value} to any of the types in {target_type}")
    elif origin_type in {tuple, Tuple}:
        elem_types = get_args(target_type)
        if elem_types[-1] is Ellipsis:
            elem_type = elem_types[0]
            return tuple(_wrangle_type(field_name, v, elem_type) for v in value)
        else:
            return tuple(_wrangle_type(field_name, v, t) for v, t in zip(value, elem_types))
    elif target_type is type(None):
        if value is not None:
            raise ValueError(f"Cannot convert {value} to {target_type}")
        return None
    elif target_type in BASE_TYPES:
        try:
            return target_type(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value} to {target_type}")
    else:
        raise ValueError(f"Field {field_name} should have only this immutable typehints: None, tuple, {BASE_TYPES}")


class BaseScheme:
    def __init__(self):
        self._before_interpolation = {}
        self._after_interpolation = {}
        self._is_frozen = False

        # ==== convert all on init
        param_name_to_type_hint = get_type_hints(self)
        for field_name, field_type in param_name_to_type_hint.items():
            given_value = self._get_value(field_name)

            # don't work on empty field
            if given_value == EMPTY_FIELD:
                continue

            converted_value = _wrangle_type(field_name, given_value, field_type)
            setattr(self, field_name, converted_value)

    def _get_value(self, field_name):
        given_value = getattr(self, field_name, EMPTY_FIELD)
        return given_value

    def override_from_dict(self, changed_params: dict[str, Any]):
        param_name_to_type_hint = get_type_hints(self)
        for param_name, value in changed_params.items():
            if param_name not in param_name_to_type_hint:
                raise RuntimeError(f"param name {param_name} does not exist")

            field_type = param_name_to_type_hint[param_name]
            value = _wrangle_type(param_name, value, field_type)
            setattr(self, param_name, value)

    def override_from_cli(self):
        argv = sys.argv[1:]  # Skip the script name
        if len(argv) % 2 != 0:
            raise RuntimeError(
                "Got odd amount of space separated strings as CLI inputs. Must be even as '--key value' pairs"
            )
        for i in range(0, len(argv), 2):
            key = argv[i]
            if not key.startswith("--"):
                raise RuntimeError(f"Invalid argument key: {key}. Argument keys must start with '--'.")
            key = key.lstrip("-")
            value = argv[i + 1]
            self.override_from_dict({key: value})

    def override_from_yaml(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            return

        with open(filepath) as stream:
            changed_params = yaml.safe_load(stream)
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
                    f"Parameter names '{param_name}' and '{conflicting_name}' conflict when considered in lowercase."
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
        return {field_name: getattr(self, field_name) for field_name in param_name_to_type_hint}

    def save_yaml(self, filepath: str) -> None:
        if not self._is_frozen:
            raise RuntimeError("'save_yaml' only works on frozen params. please run freeze() first")

        with open(filepath, "w") as outfile:
            yaml.dump(self.to_dict(), outfile)

    def freeze(self) -> None:
        param_name_to_type_hint = get_type_hints(self)
        for field_name in param_name_to_type_hint:
            # check empty field
            if self._get_value(field_name) == EMPTY_FIELD:
                raise ValueError(f"{field_name} is empty and must be set before freeze()")

        self._is_frozen = True

    def __setattr__(self, key, value):
        # NOTE: in the init phase _is_frozen is not yet declared, but setattr is called when we make new vars, so we default to False here
        if getattr(self, "_is_frozen", False):
            raise AttributeError(f"Params are frozen. Cannot modify attribute {key}")
        super().__setattr__(key, value)
