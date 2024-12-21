import enum
import json
import os
from pathlib import Path
from typing import Any, get_args, get_origin

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
            raise ValueError(f"Expected a dictionary, got {data}")
        for field_name, field_info in cls.model_fields.items():
            _validate_immutable_typehint(field_name, field_info.annotation)

            outer_type = get_origin(field_info.annotation)
            inner_args = get_args(field_info.annotation)
            if outer_type is np.ndarray:
                data[field_name] = np.array(field_info.get_default())
            # if isinstance(var, BaseParams):
            #     var._validate_immutable_typehints()
            # else:
            #
        return data

        if isinstance(data, dict):
            if "card_number" in data:
                raise ValueError("'card_number' should not be included")
        else:
            raise ValueError(f"Expected a dictionary, got {data}")
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


# class Test(BaseParams):
#     param: int = 5


# t = Test()


# class Test2(Test):
#     param2: int = 10


# t2 = Test2()

import warnings
from enum import Enum
from pathlib import Path
from typing import Literal, Optional, Tuple, Union

import numpy as np

warnings.filterwarnings("error")


# Define Enums
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class StatusCode(Enum):
    SUCCESS = 200
    CLIENT_ERROR = 400
    SERVER_ERROR = 500


class A(BaseParams):
    np01: np.ndarray[int] = np.array([1, 2, 3])
    np02: np.ndarray[int] = [1, 2, 3]
    # np03: np.ndarray[float] | None = [[1, 2, 3], [4, 5, 6]]

    # For int
    i01: int = 1
    i03: int | None = None
    i04: int | float = 8
    i05: int | str = 9

    # For str
    s01: str = "xyz"
    s03: str | None = None
    s04: str = "default"
    s05: str | int = "77"

    # For float
    f01: float = 0.5
    f03: float | None = None
    f04: float = 8.5

    # For bool
    b03: bool | None = None
    b04: bool = True

    # For bytes
    by01: bytes | None = None
    by02: bytes = b"default"
    # by03: bytes = "default"  # string

    # For Path
    p01: Path = "/tmp/yy"
    p02: Path | None = None
    p03: Path = Path("/xx/path")

    # literals
    l01: Literal["a", "b", "c"] = "a"

    # tuples
    t01: tuple[int, int] = (640, 480)
    t02: tuple[int, str] = (1, "2")
    t03: tuple[tuple[int, str], tuple[float, str]] = ((1, "a"), (3.14, "b"))
    t04: tuple[int, int, int] | None = (1, 2, 3)
    t05: tuple[int | str, ...] = ("key1", 1)

    # old typehints
    o01: Tuple[Tuple[int, str], Tuple[float, str]] = ((1, "a"), (3.14, "b"))
    o02: Optional[Tuple[int, int, int]] = (1, 2, 3)
    o03: Union[int, float] = 42
    o04: Tuple[Union[int, str], ...] = ("key1", 1)

    # enums
    e01: Color = Color.RED
    e02: StatusCode = StatusCode.SUCCESS


class B(A):
    """
    all fields from above are fields here + a complex field that also has all
    """

    bp01: A = A()
    bp02: A | None = A()
    bp03: A | None = None


class MyParams(B):
    xxx: int = 1


x = MyParams()
