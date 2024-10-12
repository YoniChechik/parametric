import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_serializer

from parametric._typehints import _validate_immutable_typehint


class BaseParams(BaseModel):
    def __init__(self, *args, **kwargs):
        # currently i don't know a way to set private vars because it will be a part of the model
        super().__init__(*args, **kwargs)
        self._validate_immutable_typehints()

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
        # based on: https://github.com/pydantic/pydantic/discussions/3139#discussioncomment-4797649
        update = self.model_dump()
        update.update(data)
        for k, v in self.model_validate(update).model_dump(exclude_defaults=True).items():
            setattr(self, k, v)

    def override_from_yaml_file(self, yaml_path: Path | str):
        with open(yaml_path, "r") as file:
            yaml_data = yaml.safe_load(file)
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
        self.model_config["frozen"] = True
        for field_name, field_info in self.model_fields.items():
            if isinstance(field_info.annotation, type) and issubclass(field_info.annotation, BaseParams):
                inner_base_params: BaseParams = getattr(self, field_name)
                inner_base_params.model_config["frozen"] = True

    # ==== serializing
    @field_serializer("*", when_used="json")
    def serialize_path_to_str(self, value):
        if isinstance(value, Path):
            return str(value.as_posix())
        return value

    def model_dump_serializable(self):
        return json.loads(self.model_dump_json())

    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            if getattr(self, field_name) != getattr(other, field_name):
                return False
        return True
