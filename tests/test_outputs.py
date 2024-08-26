import copy
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from parametric import BaseParams


class MyValidationParams(BaseParams):
    validation_batch_size: int = 8
    validation_save_dir: Path = Path("/my_dir")


class MyParams(BaseParams):
    data_dirs: tuple[str, ...]
    num_classes_without_bg: int | None = None
    dataset_name: str | None = None
    image_shape: tuple[int, int] = (640, 640)
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    save_dir_path: str | None = None
    num_epochs: int = 1000
    train_batch_size: int = 12
    val_batch_size: int = 36
    validation_step_per_epochs: int = 1
    init_lr: float = 1e-4
    lr_scheduler_patience_in_validation_steps: int = 20
    lr_scheduler_factor: float = 0.5
    continue_train_dir_path: str | None = None
    continue_train_is_reset_to_init_lr: bool = False
    res_dir: Path = Path("/my_res_path")
    validation: MyValidationParams = MyValidationParams()


@pytest.fixture
def params():
    # Return a deep copy of the params to ensure each test gets a fresh instance
    return copy.deepcopy(MyParams())


def test_save_yaml(params: MyParams):
    params.num_epochs = 500
    params.num_classes_without_bg = 3
    params.train_batch_size = 8
    params.val_batch_size = 32
    params.data_dirs = ("x", "Y")

    params.freeze()

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    os.remove(tmp_yaml_name)

    expected_yaml = (
        "continue_train_dir_path: null\n"
        "continue_train_is_reset_to_init_lr: false\n"
        "data_dirs:\n"
        "- x\n"
        "- Y\n"
        "dataset_name: null\n"
        "image_shape:\n"
        "- 640\n"
        "- 640\n"
        "init_lr: 0.0001\n"
        "lr_scheduler_factor: 0.5\n"
        "lr_scheduler_patience_in_validation_steps: 20\n"
        "nn_default_encoder_weights: imagenet\n"
        "nn_encoder_name: efficientnet-b0\n"
        "num_classes_without_bg: 3\n"
        "num_epochs: 500\n"
        f"res_dir: {os.sep}my_res_path\n"
        "save_dir_path: null\n"
        "train_batch_size: 8\n"
        "val_batch_size: 32\n"
        "validation:\n"
        "  validation_batch_size: 8\n"
        f"  validation_save_dir: {os.sep}my_dir\n"
        "validation_step_per_epochs: 1\n"
    )

    _compare_strings_with_multiple_newlines(loaded_params, expected_yaml)


def _compare_strings_with_multiple_newlines(string1: str, string2: str) -> None:
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()

    for i, (line1, line2) in enumerate(zip(lines1, lines2)):
        if line1 != line2:
            raise Exception(f"Difference at line {i+1}:\n String 1: {line1}\nString 2: {line2}")

    if len(lines1) != len(lines2):
        raise Exception("Not same amount of lines")


def test_to_dict(params: MyParams):
    params = MyParams()
    params.num_epochs = 500
    params.num_classes_without_bg = 3
    params.train_batch_size = 8
    params.val_batch_size = 32
    params.data_dirs = ("x", "Y")

    params.freeze()

    params_dict = params.to_dict()
    assert params_dict["num_epochs"] == 500
    assert params_dict["num_classes_without_bg"] == 3
    assert params_dict["train_batch_size"] == 8
    assert params_dict["val_batch_size"] == 32


if __name__ == "__main__":
    pytest.main(["-v", __file__])
