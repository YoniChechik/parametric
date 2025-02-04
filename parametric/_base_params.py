from pathlib import Path
from typing import Any

import msgpack
import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_serializer, field_validator
from pydantic_core import PydanticUndefined

from parametric._context_manager import IS_FREEZE, Override
from parametric._field_eq_check import is_equal_field
from parametric._serializers import decode_custom, encode_custom
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
        # to allow numpy- we are overriding the validation process anyway
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
        # already in override() context:
        if not IS_FREEZE.res:
            self._override_for_loop(data)
        else:
            with Override():
                self._override_for_loop(data)

    def _override_for_loop(self, data: dict[str, Any]):
        for k, v in data.items():
            # NOTE: this also validates
            setattr(self, k, v)

    # ==== serializing
    @field_serializer("*", when_used="json")
    def _json_serialize_helper(self, value: Any) -> Any:
        # === path to str
        if isinstance(value, Path):
            return str(value.as_posix())
        # === numpy to list
        if isinstance(value, np.ndarray):
            return value.tolist()
        # === tuple (recursively)
        if isinstance(value, tuple):
            return tuple(self._json_serialize_helper(item) for item in value)
        return value

    def model_dump_serializable(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}

        # NOTE: first we must find all undefined and override them in the default params instance
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
        dict_res = self.model_dump()
        with open(save_path, "wb") as file:
            file.write(msgpack.packb(dict_res, default=encode_custom))

    def override_from_msgpack_path(self, msgpack_path: Path | str) -> None:
        msgpack_data = _load_from_msgpack_path(msgpack_path)
        self.override_from_dict(msgpack_data)

    @classmethod
    def load_from_msgpack_path(cls, msgpack_path: Path | str):
        msgpack_data = _load_from_msgpack_path(msgpack_path)
        return cls(**msgpack_data)

    # ====== yaml
    def save_yaml(self, save_path: str | Path) -> None:
        with open(save_path, "w") as file:
            yaml.dump(self.model_dump_serializable(), file)

    def override_from_yaml_path(self, yaml_path: Path | str) -> None:
        yaml_data = _open_yaml_file(yaml_path)
        self.override_from_dict(yaml_data)

    @classmethod
    def load_from_yaml_path(cls, yaml_path: Path | str):
        yaml_data = _open_yaml_file(yaml_path)

        return cls(**yaml_data)

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
        if IS_FREEZE.res:
            raise AttributeError("Instance is frozen")
        self.model_config["frozen"] = False
        try:
            res = super().__setattr__(name, value)
        finally:
            self.model_config["frozen"] = True

        return res


def _open_yaml_file(yaml_path: Path | str) -> dict[str, Any]:
    _validate_filepath(yaml_path)

    with open(yaml_path, "r") as file:
        yaml_data = yaml.safe_load(file)
    # None returns if file is empty
    if yaml_data is None:
        yaml_data = {}
    return yaml_data


def _validate_filepath(filepath: Path | str) -> Path:
    filepath = Path(filepath)
    if not filepath.is_file():
        raise FileNotFoundError(f"No such file: '{filepath}'")
    return filepath


def _load_from_msgpack_path(msgpack_path: Path | str):
    _validate_filepath(msgpack_path)

    with open(msgpack_path, "rb") as file:
        msgpack_data = msgpack.unpackb(file.read(), object_hook=decode_custom)
    return msgpack_data
