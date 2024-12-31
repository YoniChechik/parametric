import copy

import numpy as np
import pytest

from parametric import BaseParams
from tests.conftest import MyParams
from tests.tmp_file_context import CreateTmpFile


def test_yaml_overrides(params: MyParams):
    with CreateTmpFile(suffix=".yaml", data="f04: 0.001\nnp01: \n- 1 \n- 2") as tmp_yaml:
        params.override_from_yaml_path(tmp_yaml.filepath)

    assert params.f04 == 0.001
    assert np.array_equal(params.np01, [1, 2])


def test_non_existent_yaml_file(params: MyParams):
    non_existent_file = "non_existent_file.yaml"
    with pytest.raises(Exception) as exc_info:
        params.override_from_yaml_path(non_existent_file)
    assert "No such file: 'non_existent_file.yaml'" in str(exc_info.value)


def test_empty_yaml_overrides(params: MyParams):
    original_params = copy.deepcopy(params)

    with CreateTmpFile(suffix=".yaml", data="\n") as tmp_yaml:
        params.override_from_yaml_path(tmp_yaml.filepath)

    assert params == original_params


def test_load_from_yaml():
    class Test(BaseParams):
        f01: float
        f02: float = 0
        f03: float = 0.1

    with CreateTmpFile(suffix=".yaml", data="f01: 0.1\nf02: 0.2\n") as tmp_yaml:
        t = Test.load_from_yaml_path(tmp_yaml.filepath)

    assert t.f01 == 0.1
    assert t.f02 == 0.2
    assert t.f03 == 0.1


def test_save_yaml(params: MyParams):
    with CreateTmpFile(suffix=".yaml") as tmp_yaml:
        params.save_yaml(tmp_yaml.filepath)

        with open(tmp_yaml.filepath) as f:
            loaded_params = f.read()

        # Check for various strings in the YAML
        _check_strings_in_yaml(loaded_params, "\nb04: true\n")
        _check_strings_in_yaml(loaded_params, "\nt01:\n- 640\n- 480\n")
        _check_strings_in_yaml(loaded_params, "\nnp03:\n- - 1\n  - 2\n  - 3\n")
        _check_strings_in_yaml(loaded_params, "\nbp01:\n  b03: null\n")

        # Reload params and ensure equality
        params2 = MyParams()
        params2.override_from_yaml_path(tmp_yaml.filepath)

    assert params == params2


def _check_strings_in_yaml(yaml_content: str, expected_substring: str) -> None:
    assert expected_substring in yaml_content, f"Expected substring not found in YAML:'''\n{expected_substring}\n'''"
