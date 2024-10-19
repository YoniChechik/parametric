import os
import sys
from tempfile import NamedTemporaryFile

import pytest

from parametric._base_params import BaseParams
from tests.conftest import MyParams


class MyValidationParams(BaseParams):
    validation_batch_size: int = 8
    validation_save_dir: Path = Path("/my_dir")


class MyParams(BaseParams):
    num_classes_without_bg: int = 5
    scheduler_name: str | None = None
    image_shape: tuple[int, int] = (640, 480)
    dataset_name: Literal["a", "b", "c"] = "a"
    nn_encoder_name: str = "efficientnet-b0"
    save_dir_path: Path | None = Path("/my/path")
    complex_number: complex = 1000 + 1j
    some_bytes: bytes = b"abc123"
    init_lr: float = 1e-4
    is_dropout: bool = False
    data_dirs: tuple[Path, ...]
    validation: MyValidationParams = MyValidationParams()


def test_cli_overrides(monkeypatch):
    # Setup mock command line arguments
    test_args = "script_name.py --dataset_name c --num_classes_without_bg 3".split()

    monkeypatch.setattr(sys, "argv", test_args)

    params.override_from_cli()

    assert params.i01 == 11
    assert params.s01 == "aaa"


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, params: MyParams):
    # Setup mock environment variables
    monkeypatch.setenv("_param_f03", "12.5")

    params.override_from_envs()

    assert params.f03 == 12.5


def test_yaml_overrides(params: MyParams):
    # Mock YAML file content
    yaml_content = "f04: 0.001"

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params.override_from_yaml_file(tmp_yaml_name)

    assert params.f04 == 0.001

    os.remove(tmp_yaml_name)


def test_combined_overrides(monkeypatch: pytest.MonkeyPatch, params: MyParams):
    # Setup mock command line arguments
    test_args = "script_name.py --i01 11 --s01 aaa".split()
    monkeypatch.setattr(sys, "argv", test_args)

    # Setup mock environment variables
    monkeypatch.setenv("_param_f03", "12.5")

    # Mock YAML file content
    yaml_content = "f04: 0.001"
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params.override_from_cli()
    params.override_from_yaml_file(tmp_yaml_name)
    params.override_from_envs()

    os.remove(tmp_yaml_name)

    assert params.i01 == 11
    assert params.s01 == "aaa"
    assert params.f03 == 12.5
    assert params.f04 == 0.001

    assert params.model_dump_non_defaults() == {"i01": 11, "s01": "aaa", "f03": 12.5, "f04": 0.001}


def test_dict_overrides():
    class Test(BaseParams):
        i1: int = 1

    params = Test()
    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"i1": "test"})
    assert (
        "Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='test', input_type=str]"
        in str(exc_info.value)
    )
