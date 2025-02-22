import enum
from dataclasses import dataclass
from pathlib import Path
from types import UnionType
from typing import Any, Type, get_args

from typing_extensions import dataclass_transform  # we can import directly from typing on version >= python3.11

from parametric._field_eq_check import is_equal_field
from parametric._io import process_filepath
from parametric._msgpack import BaseParamsData, EnumData, pack_obj, unpack_obj
from parametric._process import process_field


# TODO idea: make this package dataclass++ where we can derive from msgpack or yaml or just reguler validation coercion checks + immutables only
class _UNSET_FIELD:
    pass


UNSET_FIELD = _UNSET_FIELD()


# TODO work on this shit
@dataclass(frozen=True)
class OnInitConfig:
    """Configuration settings for MyDataclass subclasses."""

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

        # Prevent overriding critical methods
        for method in ("__init__", "__new__", "__init_subclass__", "__post_init__"):
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
            if k not in self._get_annotations():
                raise AttributeError(f"`{k}` is not a valid field in {self.__class__.__name__}")
            super().__setattr__(k, v)

        if self.__on_init_config__.validate_on_init:
            self.validate()

    def validate(self):
        for name, declared_type in self._get_annotations().items():
            input_value = getattr(self, name)
            result = process_field(name, declared_type, input_value, strict=self.__on_init_config__.validate_on_init)
            if result is not None and result.is_coerced:
                setattr(self, name, result.coerced_value)

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}
        for field_name in self.__class__._get_annotations():
            default_value = getattr(self.__class__, field_name, UNSET_FIELD)
            if default_value is UNSET_FIELD:
                changed[field_name] = getattr(self, field_name)
                continue

            current_value = getattr(self, field_name)
            if isinstance(current_value, BaseParams):
                nested_changed = current_value.model_dump_non_defaults()
                if nested_changed:
                    changed[field_name] = nested_changed
                continue

            if not is_equal_field(default_value, current_value):
                changed[field_name] = current_value

        return changed

    def save_msgpack(self, save_path: str | Path) -> None:
        with open(save_path, "wb") as f:
            pack_obj(self.__dict__, f)

    @classmethod
    def load_msgpack(cls, msgpack_path: Path | str):
        msgpack_path = process_filepath(msgpack_path)

        path = Path(msgpack_path)
        with open(path, "rb") as f:
            loaded_data = unpack_obj(f)

        return cls._postprocess_msgpack(loaded_data)

    @classmethod
    def _postprocess_msgpack(cls, unpacked_dict: dict[str, Any]):
        annotations = cls._get_annotations()
        for k in unpacked_dict:
            k_type = annotations[k]
            # TODO for union handle the possibility of N of type baseparams/enum/sequence
            if isinstance(unpacked_dict[k], BaseParamsData):
                # Handle nested BaseParamsData
                if type(k_type) is UnionType:
                    for inner_type in get_args(k_type):
                        if issubclass(inner_type, BaseParams):
                            break
                    base_params_class: BaseParams = inner_type
                else:
                    base_params_class: BaseParams = k_type

                unpacked_dict[k] = base_params_class._postprocess_msgpack(unpacked_dict[k].param_dict)
            elif isinstance(unpacked_dict[k], EnumData):
                # Handle EnumData
                if type(k_type) is UnionType:
                    for inner_type in get_args(k_type):
                        if isinstance(inner_type, enum.EnumMeta):
                            break
                    enum_class: enum.EnumMeta = inner_type
                else:
                    enum_class: enum.EnumMeta = k_type
                unpacked_dict[k] = enum_class[unpacked_dict[k].value_name]
            # TODO handle sequence like...

        # TODO i dont want to validate and coerce here
        return cls(**unpacked_dict)

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
        if name not in self._get_annotations():
            raise AttributeError(f"`{name}` is not a valid field in {self.__class__.__name__}")
        return super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={repr(v)}" for k, v in self.__dict__.items()]
        return f"{self.__class__.__name__}({', '.join(items)})"
