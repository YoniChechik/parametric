import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_serializer, field_validator
from pydantic_core import PydanticUndefined

from parametric._context_manager import IS_FREEZE, Override
from parametric._field_eq_check import is_equal_field
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

    # NOTE: args/kwargs are needed to make change on init work
    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

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
        if not IS_FREEZE.res:
            raise Exception("Do not use 'override_...' functionality inside 'Override' context manager")

        with Override():
            for k, v in data.items():
                # NOTE: this also validates
                setattr(self, k, v)

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _serialize_helper(self, value: Any) -> Any:
        # === path to str
        if isinstance(value, Path):
            return str(value.as_posix())
        # === numpy to list
        if isinstance(value, np.ndarray):
            return value.tolist()
        # === tuple to list (recursively)
        if isinstance(value, tuple):
            return [self._serialize_helper(item) for item in value]
        return value

    def model_dump_serializable(self) -> dict[str, Any]:
        return json.loads(self.model_dump_json())

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}

        # NOTE: first we must find all undefined and overrid them in the default params instance
        undefined_override_dict = {}
        for field_name, field_info in self.model_fields.items():
            default_value_not_validated = field_info.get_default()
            if default_value_not_validated is PydanticUndefined:
                undefined_override_dict[field_name] = getattr(self, field_name)

        default_params = self.__class__(**undefined_override_dict)
        for field_name in self.model_fields:
            current_value = getattr(self, field_name)
            if field_name in undefined_override_dict:
                changed[field_name] = current_value
                continue
            if isinstance(current_value, BaseParams):
                nested_changed = current_value.model_dump_non_defaults()
                if nested_changed:
                    changed[field_name] = nested_changed
                continue
            default_value = getattr(default_params, field_name)

            if not is_equal_field(default_value, current_value):
                changed[field_name] = current_value

        return changed

    # ====== msgpack
    def save_msgpack(self, save_path: str | Path) -> None:
        import msgpack

        with open(save_path, "wb") as file:
            file.write(msgpack.packb(self.model_dump_serializable()))

    def override_from_msgpack_file(self, msgpack_path: Path | str) -> None:
        import msgpack

        filepath = Path(msgpack_path)
        if not filepath.is_file():
            return

        with open(msgpack_path, "rb") as file:
            msgpack_data = msgpack.unpackb(file.read())
        self.override_from_dict(msgpack_data)

    # ====== yaml
    def save_yaml(self, save_path: str | Path) -> None:
        with open(save_path, "w") as file:
            yaml.dump(self.model_dump_serializable(), file)

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

    # ===== equality check
    def __eq__(self, other: "BaseParams") -> bool:
        if not isinstance(other, BaseParams):
            return False
        for field_name in self.model_fields:
            if field_name not in other.model_fields:
                return False
            if not is_equal_field(getattr(self, field_name), getattr(other, field_name)):
                return False
        return True

    # ==== setter with freeze check
    def __setattr__(self, name, value):
        self._set_freeze(IS_FREEZE.res)
        return super().__setattr__(name, value)

    def _set_freeze(self, is_frozen: bool):
        for field_name in self.model_fields:
            var = getattr(self, field_name)
            if isinstance(var, BaseParams):
                var._set_freeze(is_frozen)
            elif isinstance(var, np.ndarray):
                var.flags.writeable = not is_frozen
        self.model_config["frozen"] = is_frozen
