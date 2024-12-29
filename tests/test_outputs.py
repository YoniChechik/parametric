import os
from tempfile import NamedTemporaryFile

from tests.conftest import MyParams


def test_save_yaml(params: MyParams):
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    # Check for various strings in the YAML
    _check_strings_in_yaml(loaded_params, "b04: true")
    _check_strings_in_yaml(loaded_params, "t01:\n- 640\n- 480")
    _check_strings_in_yaml(loaded_params, "np03:\n- - 1\n  - 2\n  - 3")

    # Reload params and ensure equality
    params2 = MyParams()
    params2.override_from_yaml_file(tmp_yaml_name)

    os.remove(tmp_yaml_name)
    assert params == params2


def _check_strings_in_yaml(yaml_content: str, expected_substring: str) -> None:
    """Check if the expected substring exists in the YAML content, don't care about whitespaces."""
    normalized_content = "".join(yaml_content.split())
    normalized_substring = "".join(expected_substring.split())
    assert normalized_substring in normalized_content, f"Expected substring not found in YAML:\n{expected_substring}\n"


def test_model_dump_serializable(params: MyParams):
    params_dict = params.model_dump_serializable()
    assert params_dict["p03"] == "/xx/path"


def test_model_dump_non_defaults(params: MyParams):
    params.override_from_dict({"f04": 0.001})
    assert params.f04 == 0.001

    assert params.model_dump_non_defaults() == {"f04": 0.001}


def test_msgpack(params: MyParams):
    with NamedTemporaryFile("wb", delete=False, suffix=".msgpack") as tmp_msgpack:
        tmp_msgpack_name = tmp_msgpack.name
        params.save_msgpack(tmp_msgpack_name)

    # Reload params and ensure equality
    params2 = MyParams()
    params2.override_from_msgpack_file(tmp_msgpack_name)

    os.remove(tmp_msgpack_name)
    assert params == params2
