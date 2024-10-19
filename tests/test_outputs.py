import os
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
    params.freeze()

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    expected_yaml = "b03: null\nb04: true\nbp01:\n  b03: null\n  b04: true\n  by03: null\n  by04: default\n  e01: red\n  e02: 200\n  f01: 0.5\n  f03: null\n  f04: 8.5\n  i01: 1\n  i03: null\n  i04: 8\n  i05: 9\n  l01: a\n  o01:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  o02:\n  - 1\n  - 2\n  - 3\n  o03: 42\n  o04:\n  - key1\n  - 1\n  p03: null\n  p04: /xx/path\n  s01: xyz\n  s03: null\n  s04: default\n  s05: '77'\n  t01:\n  - 640\n  - 480\n  t02:\n  - 1\n  - '2'\n  t03:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  t04:\n  - 1\n  - 2\n  - 3\n  t05:\n  - key1\n  - 1\nby03: null\nby04: default\ne01: red\ne02: 200\nf01: 0.5\nf03: null\nf04: 8.5\ni01: 1\ni03: null\ni04: 8\ni05: 9\nl01: a\no01:\n- - 1\n  - a\n- - 3.14\n  - b\no02:\n- 1\n- 2\n- 3\no03: 42\no04:\n- key1\n- 1\np03: null\np04: /xx/path\ns01: xyz\ns03: null\ns04: default\ns05: '77'\nt01:\n- 640\n- 480\nt02:\n- 1\n- '2'\nt03:\n- - 1\n  - a\n- - 3.14\n  - b\nt04:\n- 1\n- 2\n- 3\nt05:\n- key1\n- 1\n"

    _compare_strings_with_multiple_newlines(loaded_params, expected_yaml)

    params2 = MyParams()
    params2.override_from_yaml_file(tmp_yaml_name)

    os.remove(tmp_yaml_name)
    assert params == params2

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
    params.freeze()

    params_dict = params.model_dump_serializable()
    assert params_dict["p04"] == "/xx/path"
