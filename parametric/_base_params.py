import enum
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from parametric._validate_immutable_typehint import _validate_immutable_typehint


class BaseParams(BaseModel):
    model_config = ConfigDict(
        # validate after each assignment
        validate_assignment=True,
        # frozen after init
        frozen=True,
        # don't allow new fields after init
        extra="forbid",
        # validate default values
        validate_default=True,
        # allow arbitrary types (only to add numpy)
        arbitrary_types_allowed=True,
    )

    @model_validator(mode="before")
    @classmethod
    def to_numpy(cls, data: Any) -> Any:
        for field_name, field_info in cls.model_fields.items():
            # TODO can be in a tuple or union
            if field_info.annotation == np.ndarray:
                arr = np.asarray(field_info.get_default())
                arr.flags.writeable = False

                data[field_name] = arr

        return data

    @model_validator(mode="after")
    def _validate_immutable_typehints(self):
        for field_name, field_info in self.model_fields.items():
            var = getattr(self, field_name)
            # if isinstance(var, BaseParams) -> already validated on creation
            if not isinstance(var, BaseParams):
                _validate_immutable_typehint(field_name, field_info.annotation)
        return self

    def override_from_dict(self, data: dict[str, Any]):
        self._set_freeze(False)
        for k, v in data.items():
            # NOTE: this also validates
            setattr(self, k, v)
        self._set_freeze(True)

    def _set_freeze(self, is_frozen: bool):
        for field_name in self.model_fields:
            var = getattr(self, field_name)
            if isinstance(var, BaseParams):
                var._set_freeze(is_frozen)
        self.model_config["frozen"] = is_frozen

    def model_dump_non_defaults(self):
        changed = {}
        default_params = self.__class__()
        default_params._set_freeze(False)
        for field_name in self.model_fields:
            if not self._is_equal_field(field_name, default_params):
                changed[field_name] = getattr(self, field_name)
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

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _serializer(self, value):
        # === path to linux path to string
        if isinstance(value, Path):
            return str(value.as_posix())
        # === numpy to list
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def model_dump_serializable(self):
        return json.loads(self.model_dump_json())

    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            if not self._is_equal_field(field_name, other):
                return False
        return True

    def _is_equal_field(self, field_name: str, other: "BaseParams"):
        self_val = getattr(self, field_name)
        other_val = getattr(other, field_name)
        # not same type
        if not isinstance(self_val, type(other_val)):
            return False
        # for np.ndarray
        if isinstance(self_val, np.ndarray):
            return np.array_equal(self_val, other_val)
        # for enums
        if isinstance(self_val, enum.Enum) and self_val.value == other_val.value:
            return True
        # for all others
        if self_val == other_val:
            return True
        return False
