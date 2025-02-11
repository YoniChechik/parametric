import enum
from dataclasses import dataclass
from pathlib import Path
from types import UnionType
from typing import Any, Type

import msgpack
import numpy as np
import yaml
from typing_extensions import dataclass_transform, get_args

from parametric._field_eq_check import is_equal_field
from parametric._io import load_from_yaml_path, process_filepath
from parametric._validate import process_field

# TODO add test of @property


# TODO work on this shit
@dataclass(frozen=True)
class OnInitConfig:
    """Configuration settings for MyDataclass subclasses."""

    immutable: bool = False
    validate_assignment: bool = True
    validate_on_init: bool = True
    coerce_when_validating: bool = False


# @dataclass_transform is a decorator that helps typecheckers and IDEs understand the dataclass-like behavior of the class.
@dataclass_transform()
class BaseParams:
    """Base class mimicking dataclass behavior with configurable settings."""

    __on_init_config__ = OnInitConfig()

    def __init_subclass__(cls):
        super().__init_subclass__()

        # TODO is needed?
        # Ensure the subclass has its own func, inheriting if not overridden
        if not hasattr(cls, "__on_init_config__"):
            cls.__on_init_config__ = cls.__base__.__on_init_config__

        # Prevent overriding critical methods
        for method in ("__init__", "__new__", "__init_subclass__"):
            if method in cls.__dict__:
                raise TypeError(f"Subclasses cannot override {method}.")

    # NOTE: args/kwargs are needed to make change on init work
    def __new__(cls, *args, **kwargs):
        if cls is BaseParams:
            raise TypeError(f"{cls.__name__} cannot be instantiated directly, only derive from")
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        super().__init__()
        if len(args) > 0:
            raise ValueError("BaseParams does not accept positional arguments")

        # set default values from instantiated class
        for k, v in kwargs.items():
            setattr(self, k, v)

        if self.__on_init_config__.validate_on_init:
            self.validate()

        # TODO how to get default values? for list the pointers can change later
        # self.defaults = None
        self._after_init = True

    def validate(self):
        for name, declared_type in self._get_annotations().items():
            input_value = getattr(self, name)
            res = process_field(name, declared_type, input_value, strict=self.__on_init_config__.coerce_when_validating)
            if res is not None:
                setattr(self, name, res)
            setattr(self, name, input_value)

    def _override_for_loop(self, data: dict[str, Any]):
        for k, v in data.items():
            # NOTE: this also validates
            setattr(self, k, v)

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}

        default_params = self.__class__()
        for field_name in self._get_annotations():
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
    @classmethod
    def msgpack_custom_decode(cls, obj: Any) -> Any:
        # Handle numpy arrays
        if "__ndarray__" in obj:
            array = np.frombuffer(obj["data"], dtype=obj["dtype"])
            return array.reshape(obj["shape"])
        # Handle pathlib.Path
        if "__pathlib__" in obj:
            return Path(obj["as_posix"])
        # if "__BaseParams__" in obj:
        #     return obj["data"]
        return obj

    @classmethod
    def msgpack_custom_encode(cls, obj):
        # Handle numpy arrays
        if isinstance(obj, np.ndarray):
            return {
                "__ndarray__": True,
                "data": obj.data,  # memoryview
                "dtype": str(obj.dtype),
                "shape": obj.shape,
            }
        # Handle pathlib.Path
        if isinstance(obj, Path):
            return {
                "__pathlib__": True,
                "as_posix": str(obj.as_posix()),
            }
        # Handle Enums by taking their value
        if isinstance(obj, enum.Enum):
            return obj.value

        if isinstance(obj, BaseParams):
            return {"__BaseParams__": True, "data": {name: getattr(obj, name) for name in obj._get_annotations()}}

        return obj

    def save_msgpack(self, save_path: str | Path) -> None:
        with open(save_path, "wb") as file:
            file.write(msgpack.packb(self, default=self.msgpack_custom_encode))

    @classmethod
    def load_from_msgpack_path(cls, msgpack_path: Path | str):
        msgpack_path = process_filepath(msgpack_path)

        with open(msgpack_path, "rb") as file:
            unpacked_dict = msgpack.unpackb(file.read(), object_hook=cls.msgpack_custom_decode)

        return cls._msgpack_dict_to_base_params(unpacked_dict)

    @classmethod
    def _msgpack_dict_to_base_params(cls, unpacked_dict):
        unpacked_dict = unpacked_dict["data"]
        for k in unpacked_dict:
            if isinstance(unpacked_dict[k], dict) and "__BaseParams__" in unpacked_dict[k]:
                base_params_subclass: BaseParams = cls._get_annotations()[k]
                if type(base_params_subclass) is UnionType:
                    for inner_type in get_args(base_params_subclass):
                        if issubclass(inner_type, BaseParams):
                            base_params_subclass = inner_type
                            break

                unpacked_dict[k] = base_params_subclass._msgpack_dict_to_base_params(unpacked_dict[k])
                # unpacked_dict[k] = cls._msgpack_dict_to_base_params(unpacked_dict[k])

        # TODO i dont want to validate and coerce here
        return cls(**unpacked_dict)

    # ====== yaml
    def save_yaml(self, save_path: str | Path) -> None:
        # TODO can use encoder decoder
        res = {}
        for name in self._get_annotations():
            val = getattr(self, name)
            res[name] = val

        with open(save_path, "w") as file:
            yaml.dump(res, file)

    @classmethod
    def load_from_yaml_path(cls, yaml_path: Path | str):
        yaml_data = load_from_yaml_path(yaml_path)

        return cls(**yaml_data)

    @classmethod
    def _get_annotations(cls) -> dict[str, Type]:
        # Collect __annotations__ from base classes recursively, starting from object->BaseParams->...
        annotations: dict[str, Type] = {}
        for base_cls in reversed(cls.__mro__):
            annotations.update(getattr(base_cls, "__annotations__", {}))
        return annotations

    # ===== equality check
    def __eq__(self, other: "BaseParams") -> bool:
        if not isinstance(other, BaseParams):
            return False
        for field_name in self._get_annotations():
            if field_name not in other._get_annotations():
                return False
            if not is_equal_field(getattr(self, field_name), getattr(other, field_name)):
                return False
        return True

    def __setattr__(self, name, value):
        if hasattr(self, "_after_init") and name not in self._get_annotations():
            raise AttributeError(f"`{name}` is not a valid field in {self.__class__.__name__}")
        return super().__setattr__(name, value)
