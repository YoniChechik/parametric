import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from parametric import BaseScheme


class MyParamsScheme(BaseScheme):
    data_dirs: tuple[str, ...]
    num_classes_without_bg: int | None = None
    dataset_name: str | None = None
    image_shape: tuple[int, int] = (640, 640)
    nn_encoder_name: str = "efficientnet-b0"
    nn_default_encoder_weights: str = "imagenet"
    save_dir_path: Path | None = "/my/path"
    save_dir_path2: Path | None = Path("/my/path/2")
    num_epochs: int = 10
    complex_number: complex = 1000 + 1j
    train_batch_size: int = 12
    val_batch_size: int = 36
    some_bytes: bytes = b"abc123"
    init_lr: float = 1e-4
    lr_scheduler_patience_in_validation_steps: int = 20
    lr_scheduler_factor: float = 0.5
    continue_train_dir_path: str | None = None
    continue_train_is_reset_to_init_lr: bool = False


def test_cli_overrides(monkeypatch):
    # Setup mock command line arguments
    test_args = [
        "script_name.py",
        "--num_epochs",
        "500",
        "--num_classes_without_bg",
        "3",
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    params = MyParamsScheme()
    params.override_from_cli()

    assert params.num_epochs == 500
    assert params.num_classes_without_bg == 3


def test_env_overrides(monkeypatch):
    # Setup mock environment variables
    monkeypatch.setenv("_param_val_batch_size", "32")

    params = MyParamsScheme()
    params.override_from_envs()

    assert params.val_batch_size == 32


def test_yaml_overrides():
    # Mock YAML file content
    yaml_content = "train_batch_size: 8"

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParamsScheme()
    params.override_from_yaml(tmp_yaml_name)

    assert params.train_batch_size == 8

    os.remove(tmp_yaml_name)


def test_combined_overrides(monkeypatch):
    # Setup mock command line arguments
    test_args = [
        "script_name.py",
        "--num_epochs",
        "500",
        "--num_classes_without_bg",
        "3",
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Setup mock environment variables
    monkeypatch.setenv("_param_VAL_BATCH_SIZE", "32")

    # Mock YAML file content
    yaml_content = "train_batch_size: 8"
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParamsScheme()
    params.override_from_cli()
    params.override_from_yaml(tmp_yaml_name)
    params.override_from_envs()

    os.remove(tmp_yaml_name)

    assert params.num_epochs == 500
    assert params.num_classes_without_bg == 3
    assert params.train_batch_size == 8
    assert params.val_batch_size == 32


if __name__ == "__main__":
    pytest.main(["-v", __file__])