import copy
import os
from tempfile import NamedTemporaryFile

import numpy as np

from tests.conftest import MyParams


def test_yaml_overrides(params: MyParams):
    # Mock YAML file content
    yaml_content = "f04: 0.001\nnp01: \n- 1 \n- 2"

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params.override_from_yaml_file(tmp_yaml_name)

    assert params.f04 == 0.001
    assert np.array_equal(params.np01, [1, 2])

    os.remove(tmp_yaml_name)


def test_non_existent_yaml_file(params: MyParams):
    # Test for non-existent YAML file path
    non_existent_file = "non_existent_file.yaml"
    original_params = copy.deepcopy(params)
    params.override_from_yaml_file(non_existent_file)

    assert params == original_params


def test_empty_yaml_overrides(params: MyParams):
    original_params = copy.deepcopy(params)

    # Mock YAML file content
    yaml_content = "\n"

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        tmp_yaml.write(yaml_content)

    params.override_from_yaml_file(tmp_yaml_name)

    assert params == original_params

    os.remove(tmp_yaml_name)
