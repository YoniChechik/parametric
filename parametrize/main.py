import os
import sys
from itertools import starmap
from typing import Any, Dict, List, Optional, Tuple, Union, get_type_hints

import yaml


def convert_type(value: Any, target_type: Any) -> Any:
    try:
        if target_type == Any:
            return value  # No conversion needed
        origin_type = getattr(target_type, "__origin__", None)
        if origin_type is Union:
            # Handle Optional[X] (which is Union[X, None])
            for arg in target_type.__args__:
                if arg is type(None):
                    if value is None:
                        return None
                else:
                    try:
                        return convert_type(value, arg)
                    except (ValueError, TypeError):
                        continue
            raise ValueError(f"Cannot convert {value} to {target_type}")
        elif origin_type in {list, List}:
            elem_type = target_type.__args__[0]
            return [convert_type(v, elem_type) for v in value]
        elif origin_type in {tuple, Tuple}:
            elem_types = target_type.__args__
            return tuple(starmap(convert_type, zip(value, elem_types)))
        else:
            return target_type(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value} to {target_type}")


def validate_field(field_name: str, field_type: Any, value: Any):
    origin_type = getattr(field_type, "__origin__", None)
    if origin_type is Union:
        if not any(isinstance(value, t) for t in field_type.__args__):
            raise ValueError(
                f"Field {field_name} expects type {field_type}, got {type(value)}"
            )
    elif origin_type in {list, List, tuple, Tuple}:
        if not isinstance(value, origin_type):
            raise ValueError(
                f"Field {field_name} expects type {field_type}, got {type(value)}"
            )
        elem_type = field_type.__args__[0]
        for elem in value:
            validate_field(f"{field_name} element", elem_type, elem)
    else:
        if not isinstance(value, field_type):
            raise ValueError(
                f"Field {field_name} expects type {field_type}, got {type(value)}"
            )


class ConfigBase:
    def __init__(self):
        self._before_interpolation = {}
        self._after_interpolation = {}
        self._is_frozen = False
        self.validate()

    def validate(self):
        type_hints = get_type_hints(self.__class__)
        for field_name, field_type in type_hints.items():
            # EMPTY FIELD
            if field_name not in self.__dict__:
                continue
            value = getattr(self, field_name)
            if value is not None:
                validate_field(field_name, field_type, value)

    def _override(self, changed_params: Dict[str, Any]):
        type_hints = get_type_hints(self.__class__)
        for key, value in changed_params.items():
            if key in type_hints:
                field_type = type_hints[key]
                value = convert_type(value, field_type)
                validate_field(key, field_type, value)
                setattr(self, key, value)

    def overrides_from_cli(self):
        argv = sys.argv[1:]  # Skip the script name
        assert (
            len(argv) % 2 == 0
        ), "Got odd amount of space separated strings as CLI inputs. Must be even as '--key value' pairs"
        for i in range(0, len(argv), 2):
            key = argv[i]
            assert key.startswith(
                "--"
            ), f"Invalid argument key: {key}. Argument keys must start with '--'."
            key = key.lstrip("-")
            value = argv[i + 1]
            self._override({key: value})

    def overrides_from_yaml(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            return

        with open(filepath) as stream:
            changed_params = yaml.safe_load(stream)
        if changed_params is None:
            return

        self._override(changed_params)

    def overrides_from_envs(self, env_prefix: str = "_param_") -> None:
        changed_params = {}
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                changed_params[key[len(env_prefix) :]] = value

        self._override(changed_params)

    def to_dict(self) -> Dict[str, Any]:
        type_hints = get_type_hints(self.__class__)
        return {field_name: getattr(self, field_name) for field_name in type_hints}

    def save_yaml(self, filepath: str) -> None:
        with open(filepath, "w") as outfile:
            yaml.dump(self.to_dict(), outfile)

    def freeze(self) -> None:
        self._is_frozen = True

    def __setattr__(self, key, value):
        if getattr(self, "_is_frozen", False) and key in self.__dict__:
            raise AttributeError(f"Cannot modify frozen attribute {key}")
        super().__setattr__(key, value)

    def interpolate_values(self):
        self._before_interpolation = self.to_dict()
        self._after_interpolation = self._before_interpolation.copy()

        for field_name, value in self._after_interpolation.items():
            if isinstance(value, str) and "[[" in value and "]]" in value:
                for key, val in self._after_interpolation.items():
                    if isinstance(val, str):
                        placeholder = f"[[{key}]]"
                        if placeholder in value:
                            value = value.replace(placeholder, str(val))
                self._after_interpolation[field_name] = value
                super().__setattr__(field_name, value)

        return self


class SemSegTrainParamsScheme(ConfigBase):
    data_dirs: Tuple[str, ...]
    num_classes_without_bg: Optional[int] = None
    dataset_name: Optional[str] = None
    image_shape: Tuple[int, int] = (640, 640)
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    save_dir_path: Optional[str] = None
    num_epochs: int = 1000
    train_batch_size: int = 12
    val_batch_size: int = 36
    validation_step_per_epochs: int = 1
    init_lr: float = 1e-4
    lr_scheduler_patience_in_validation_steps: int = 20
    lr_scheduler_factor: float = 0.5
    continue_train_dir_path: Optional[str] = None
    continue_train_is_reset_to_init_lr: bool = False
    test: str = "cvvfv"
    test2: str = "[[test]]+gdgd"


if __name__ == "__main__":
    sys.argv = [
        "script_name.py",
        "--num_epochs",
        "500",
        "--num_classes_without_bg",
        "3",
    ]
    config = SemSegTrainParamsScheme()

    changes_cli = config.overrides_from_cli()
    changes_yaml = config.overrides_from_yaml("config.yaml")
    changes_env = config.overrides_from_envs()

    config.save_yaml("merged_config.yaml")
    config.freeze()

    print(config.to_dict())
    config.num_classes_without_bg = 7
