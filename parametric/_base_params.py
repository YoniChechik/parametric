import enum
from pathlib import Path
from types import UnionType
from typing import Any, Type, get_args

from typing_extensions import dataclass_transform  # we can import directly from typing on version >= python3.11

from parametric._field_eq_check import is_equal_field
from parametric._io import process_filepath
from parametric._msgpack import BaseParamsData, EnumData, pack_obj, unpack_obj
from parametric._process import process_field


# TODO must work on default factory for mutables like dict,list,baseparams... otherwise the data is saved acrros different inits ofthe object since it's class level var
class _UNSET_FIELD:
    pass


UNSET_FIELD = _UNSET_FIELD()


# @dataclass_transform is a decorator that helps typecheckers and IDEs understand the dataclass-like behavior all sub-class.
# We built this class so all IDEs will recognize private params like __process__
@dataclass_transform()
class XXX:
    pass


class BaseParams(XXX):
    """Base class mimicking dataclass behavior with configurable settings."""

    __process__: bool = True

    # Add private process flag
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

    def __init__(self, **kwargs):
        super().__init__()
        if "__process__" in kwargs:
            self.__setattr__("__process__", kwargs["__process__"])
            del kwargs["__process__"]

        # set default values from instantiated class
        for k, v in kwargs.items():
            if k not in self._get_annotations():
                raise AttributeError(f"`{k}` is not a valid field in {self.__class__.__name__}")
            super().__setattr__(k, v)

        if self.__process__:
            self._process_all()

    def _process_all(self):
        for name, declared_type in self._get_annotations().items():
            input_value = getattr(self, name)
            result = process_field(name, declared_type, input_value)
            if result is not None and result.is_coerced:
                setattr(self, name, result.coerced_value)

    def model_dump_non_defaults(self) -> dict[str, Any]:
        changed = {}
        for field_name in self.__class__._get_annotations():
            default_value = getattr(self.__class__, field_name, UNSET_FIELD)
            if default_value is UNSET_FIELD:
                changed[field_name] = getattr(self, field_name)
                continue
        # TODO if baseparams is inner field it will break
        raw_class = self.__class__(**changed)

        for field_name in self.__class__._get_annotations():
            default_value = getattr(raw_class, field_name)
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
            pack_obj(self, f)

    @classmethod
    def load_msgpack(cls, msgpack_path: Path | str):
        msgpack_path = process_filepath(msgpack_path)

        path = Path(msgpack_path)
        with open(path, "rb") as f:
            loaded_data = unpack_obj(f)

        if not isinstance(loaded_data, BaseParamsData):
            raise ValueError("unpacked data is not a BaseParamsData")
        if loaded_data.class_name != cls.__name__:
            raise ValueError(
                f"unpacked data is not a BaseParamsData of the same class: {loaded_data.class_name} != {cls.__name__}"
            )

        return cls._postprocess_msgpack(loaded_data)

    @classmethod
    def _postprocess_msgpack(cls, unpacked_data: BaseParamsData):
        # TODO this is only possible if all type hints exists and validated
        # amybe lets save all enums and baseclass?
        if cls.__name__ != unpacked_data.class_name:
            raise ValueError(
                f"unpacked data is not a BaseParamsData of the same class: {unpacked_data.class_name} != {cls.__name__}"
            )
        annotations = cls._get_annotations()
        res_dict = {}
        for k in unpacked_data.param_dict:
            k_type = annotations[k]
            # TODO for union handle the possibility of N of type baseparams/enum/sequence
            if isinstance(unpacked_data.param_dict[k], BaseParamsData):
                # Handle nested BaseParamsData
                if type(k_type) is UnionType:
                    for inner_type in get_args(k_type):
                        if issubclass(inner_type, BaseParams):
                            break
                    base_params_class: BaseParams = inner_type
                else:
                    base_params_class: BaseParams = k_type

                res_dict[k] = base_params_class._postprocess_msgpack(unpacked_data.param_dict[k])
            elif isinstance(unpacked_data.param_dict[k], EnumData):
                # Handle EnumData
                if type(k_type) is UnionType:
                    for inner_type in get_args(k_type):
                        if isinstance(inner_type, enum.EnumMeta):
                            break
                    enum_class: enum.EnumMeta = inner_type
                else:
                    enum_class: enum.EnumMeta = k_type
                res_dict[k] = enum_class[unpacked_data.param_dict[k].value_name]
            # TODO handle list better
            elif isinstance(unpacked_data.param_dict[k], (list, tuple, set, frozenset)):
                res_dict[k] = unpacked_data.param_dict[k]
            else:
                res_dict[k] = unpacked_data.param_dict[k]
            # TODO handle sequence like...

        return cls(**res_dict, __process__=False)

    @classmethod
    def _get_annotations(cls) -> dict[str, Type]:
        # Collect __annotations__ from base classes recursively, starting from object->BaseParams->...
        annotations: dict[str, Type] = {}
        for base_cls in reversed(cls.__mro__):
            base_annotations = getattr(base_cls, "__annotations__", {})
            # Only include annotations that don't start with underscore
            filtered_annotations = {k: v for k, v in base_annotations.items() if not k.startswith("_")}
            annotations.update(filtered_annotations)
        return annotations

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
        if name == "__process__":
            return super().__setattr__(name, value)

        if name not in self._get_annotations():
            raise AttributeError(f"`{name}` is not a valid field in {self.__class__.__name__}")

        # Process and validate the field if process flag is enabled
        if self.__process__:
            result = process_field(name, self._get_annotations()[name], value)
            if result is not None and result.is_coerced:
                value = result.coerced_value

        return super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={repr(v)}" for k, v in self.to_dict().items()]
        return f"{self.__class__.__name__}({', '.join(items)})"

    def to_dict(self, recursive: bool = True) -> dict[str, Any]:
        """Convert the BaseParams instance to a dictionary, following reverse MRO.

        Returns:
            dict[str, Any]: Dictionary representation of the BaseParams instance
        """
        result = {}
        # Iterate through class hierarchy in reverse MRO order
        for base_cls in reversed(self.__class__.__mro__):
            annotations = getattr(base_cls, "__annotations__", {})
            for field_name in annotations:
                if field_name.startswith("_"):
                    continue
                value = getattr(self, field_name)
                # Handle nested BaseParams instances
                if isinstance(value, BaseParams) and recursive:
                    result[field_name] = value.to_dict()
                else:
                    result[field_name] = value
        return result
