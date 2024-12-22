import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_serializer, field_validator

from parametric._field_eq_check import _is_equal_field
from parametric._validate import _validate_immutable_annotation_and_coerce_np


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
        return super().__new__(cls, *args, **kwargs)

    @field_validator("*", mode="before")
    @classmethod
    def validate_and_coerce_raw_data(cls, value: Any, val_info: ValidationInfo) -> Any:
        res = _validate_immutable_annotation_and_coerce_np(
            val_info.field_name, cls.model_fields[val_info.field_name].annotation, value
        )
        if res is None:
            return value
        return res

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

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}
        default_params = self.__class__()
        for field_name in default_params.model_fields:
            default_value = getattr(default_params, field_name)
            current_value = getattr(self, field_name)
            if not _is_equal_field(default_value, current_value):
                changed[field_name] = current_value
        return changed

    def override_from_yaml_file(self, yaml_path: Path | str) -> None:
        filepath = Path(yaml_path)
        if not filepath.is_file():
            return

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

    def save_yaml(self, save_path: str | Path) -> None:
        with open(save_path, "w") as file:
            yaml.dump(self.model_dump_serializable(), file)

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _serialize_helper(self, value: Any) -> Any:
        # === path to str
        if isinstance(value, Path):
            return str(value.as_posix())
        # === numpy to list
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def model_dump_serializable(self) -> dict[str, Any]:
        return json.loads(self.model_dump_json())

    # ======== private methods =========
    def __eq__(self, other: "BaseParams") -> bool:
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            if field_name not in other.model_fields:
                return False
            if not _is_equal_field(getattr(self, field_name), getattr(other, field_name)):
                return False
        return True
