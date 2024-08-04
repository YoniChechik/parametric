import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

import pytest

from parametric import BaseParams


class MyParams(BaseParams):
    num_classes_without_bg: int = 5
    scheduler_name: str | None = None
    image_shape: tuple[int, int] = (640, 480)
    dataset_name: Literal["a", "b", "c"] = "a"
    nn_encoder_name: str = "efficientnet-b0"
    save_dir_path: Path | None = "/my/path"
    complex_number: complex = 1000 + 1j
    some_bytes: bytes = b"abc123"
    init_lr: float = 1e-4
    is_dropout: bool = False
    data_dirs: tuple[Path, ...]


def test_cli_overrides(monkeypatch):
    # Setup mock command line arguments
    test_args = "script_name.py --dataset_name c --num_classes_without_bg 3".split()

    monkeypatch.setattr(sys, "argv", test_args)

    params = MyParams()
    params.override_from_cli()

    assert params.num_classes_without_bg == 3


def test_env_overrides(monkeypatch):
    # Setup mock environment variables
    monkeypatch.setenv("_param_dataset_name", "b")

    params = MyParams()
    params.override_from_envs()

    assert params.dataset_name == "b"


def test_yaml_overrides():
    # Mock YAML file content
    yaml_content = "init_lr: 0.001"

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParams()
    params.override_from_yaml(tmp_yaml_name)

    assert params.init_lr == 0.001

    os.remove(tmp_yaml_name)


def test_combined_overrides(monkeypatch):
    # Setup mock command line arguments
    test_args = "script_name.py --num_classes_without_bg 3".split()
    monkeypatch.setattr(sys, "argv", test_args)

    # Setup mock environment variables
    monkeypatch.setenv("_param_dataset_name", "b")

    # Mock YAML file content
    yaml_content = "init_lr: 0.001"
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params = MyParams()
    params.override_from_cli()
    params.override_from_yaml(tmp_yaml_name)
    params.override_from_envs()

    os.remove(tmp_yaml_name)

    assert params.num_classes_without_bg == 3
    assert params.dataset_name == "b"
    assert params.init_lr == 0.001


if __name__ == "__main__":
    pytest.main(["-v", __file__])
