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
        # to freeze later
        frozen=True,
        # don't allow new fields after init
        extra="forbid",
        # validate default values
        validate_default=True,
        # to allow numpy
        arbitrary_types_allowed=True,
    )

    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

    @model_validator(mode="before")
    @classmethod
    def _validate_declared_types_immutables(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            raise ValueError(f"Expected a dictionary, got {type(data)}")
        for field_name, field_info in cls.model_fields.items():
            if field_name in data:
                def_value = data[field_name]
            else:
                def_value = field_info.get_default()
            fixed_value = _validate_immutable_typehint(field_name, field_info.annotation, def_value)
            if fixed_value is not None:
                data[field_name] = fixed_value

        return data

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
            elif isinstance(var, np.ndarray):
                var.flags.writeable = not is_frozen
        self.model_config["frozen"] = is_frozen

    def model_dump_non_defaults(self):
        changed = {}
        default_params = self.__class__()
        default_params._set_freeze(False)
        for field_name in self.model_fields:
            default_value = getattr(default_params, field_name)
            current_value = getattr(self, field_name)
            if current_value != default_value:
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

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _serialize_helper(self, value):
        # === path to str
        if isinstance(value, Path):
            return str(value.as_posix())
        # === numpy to list
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def model_dump_serializable(self):
        return json.loads(self.model_dump_json())

    # ======== private methods =========
    def __eq__(self, other: "BaseParams"):
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            if field_name not in other.model_fields:
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
        # TODO when overriding from dict, this is called, need to patch in np
        super().__setattr__(key, value)
