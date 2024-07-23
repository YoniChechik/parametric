import os
import sys
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
    test: str = "cvvfv"
    test2: str = "[[test]]+gdgd"


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
    params.overrides_from_cli()

    assert params.num_epochs == 500
    assert params.num_classes_without_bg == 3


def test_env_overrides(monkeypatch):
    # Setup mock environment variables
    monkeypatch.setenv("_param_val_batch_size", "32")

    params = MyParamsScheme()
    params.overrides_from_envs()

    assert params.val_batch_size == 32


def test_yaml_overrides():
    # Mock YAML file content
    yaml_content = """
    train_batch_size: 8
    """
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParamsScheme()
    params.overrides_from_yaml(tmp_yaml_name)

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
    yaml_content = """
    train_batch_size: 8
    """
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParamsScheme()
    params.overrides_from_cli()
    params.overrides_from_yaml(tmp_yaml_name)
    params.overrides_from_envs()

    os.remove(tmp_yaml_name)

    assert params.num_epochs == 500
    assert params.num_classes_without_bg == 3
    assert params.train_batch_size == 8
    assert params.val_batch_size == 32


def test_save_and_load_yaml():
    params = MyParamsScheme()
    params.num_epochs = 500
    params.num_classes_without_bg = 3
    params.train_batch_size = 8
    params.val_batch_size = 32
    params.data_dirs = ("x", "Y")

    params.freeze()

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name, "r") as f:
        loaded_params = f.read()

    os.remove(tmp_yaml_name)

    expected_yaml = "continue_train_dir_path: None\ncontinue_train_is_reset_to_init_lr: false\ndata_dirs: !!python/tuple\n- x\n- Y\ndataset_name: None\nimage_shape: !!python/tuple\n- 640\n- 640\ninit_lr: 0.0001\nlr_scheduler_factor: 0.5\nlr_scheduler_patience_in_validation_steps: 20\nnn_default_encoder_weights: imagenet\nnn_encoder_name: efficientnet-b0\nnum_classes_without_bg: 3\nnum_epochs: 500\nsave_dir_path: None\ntest: cvvfv\ntest2: '[[test]]+gdgd'\ntrain_batch_size: 8\nval_batch_size: 32\nvalidation_step_per_epochs: 1\n"
    assert loaded_params == expected_yaml


def test_freeze_params():
    params = MyParamsScheme()
    params.num_epochs = 500
    params.num_classes_without_bg = 3
    params.train_batch_size = 8
    params.val_batch_size = 32
    params.data_dirs = ("x", "Y")

    params.freeze()

    with pytest.raises(AttributeError):
        params.num_classes_without_bg = 7


def test_to_dict():
    params = MyParamsScheme()
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
