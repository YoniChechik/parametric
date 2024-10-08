import os
import sys
from tempfile import NamedTemporaryFile

import pytest

from tests.conftest import MyParams


def test_cli_overrides(monkeypatch: pytest.MonkeyPatch, params: MyParams):
    # Test for b04 set to True with different values
    for true_value in ["true", "True", "1", "t"]:
        test_args = f"script_name.py --i01 11 --s01 aaa --b04 {true_value}".split()

        monkeypatch.setattr(sys, "argv", test_args)

        params.override_from_cli()

        assert params.i01 == 11
        assert params.s01 == "aaa"
        assert params.b04 is True  # Check if b04 is correctly set to True

    # Test for b04 set to False with different values
    for false_value in ["false", "False", "0", "f"]:
        test_args = f"script_name.py --i01 11 --s01 aaa --b04 {false_value}".split()

        monkeypatch.setattr(sys, "argv", test_args)

        params.override_from_cli()

        assert params.i01 == 11
        assert params.s01 == "aaa"
        assert params.b04 is False  # Check if b04 is correctly set to False


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

    params.override_from_yaml(tmp_yaml_name)

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
    params.override_from_yaml(tmp_yaml_name)
    params.override_from_envs()

    os.remove(tmp_yaml_name)

    assert params.i01 == 11
    assert params.s01 == "aaa"
    assert params.f03 == 12.5
    assert params.f04 == 0.001


if __name__ == "__main__":
    pytest.main(["--no-cov", "-v", __file__])
