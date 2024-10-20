import enum
import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_serializer

from parametric._validate_freezable_typehint import _validate_freezable_typehint


class BaseParams(BaseModel):
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

    def model_dump_non_defaults(self):
        changed = {}
        default_params = self.model_copy()
        for field_name, field_info in self.model_fields.items():
            # fixing the problem where default from field info isn't coerced:
            # for example: a user can define Path() as parameter type but insert a default str.
            # here we coerce the default to be Path() so it's the same as the actual value
            setattr(default_params, field_name, field_info.get_default())
            # getattr of-course returns us the coerce result...
            current_value = getattr(self, field_name)
            if current_value != getattr(default_params, field_name):
                changed[field_name] = current_value
        return changed

    def override_from_yaml_file(self, yaml_path: Path | str):
        with open(yaml_path, "r") as file:
            yaml_data = yaml.safe_load(file)
        # None returns if file is empty
        if yaml_data is None:
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

        self.override_from_dict(changed_params)

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

        self.override_from_dict(changed_params)

    def save_yaml(self, save_path: str | Path):
        with open(save_path, "w") as file:
            yaml.dump(self.model_dump_serializable(), file)

    def freeze(self):
        for field_name, field_info in self.model_fields.items():
            if isinstance(field_info.annotation, type) and issubclass(field_info.annotation, BaseParams):
                inner_base_params: BaseParams = getattr(self, field_name)
                inner_base_params.freeze()
            else:
                _validate_freezable_typehint(field_name, field_info.annotation)
        self.model_config["frozen"] = True

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _serialize_path_to_str(self, value):
        if isinstance(value, Path):
            return str(value.as_posix())
        return value

    def model_dump_serializable(self):
        return json.loads(self.model_dump_json())

    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if self_val == other_val:
                continue
            # for enums
            elif (
                isinstance(self_val, enum.Enum)
                and isinstance(other_val, enum.Enum)
                and self_val.value == other_val.value
            ):
                continue
            return False
        return True
