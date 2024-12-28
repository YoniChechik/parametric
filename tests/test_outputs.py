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


"b03: null\nb04: true\nbp01:\n  b03: null\n  b04: true\n  by01: null\n  by02: default\n  e01: red\n  e02: 200\n  f01: 0.5\n  f03: null\n  f04: 8.5\n  i01: 1\n  i03: null\n  l01: a\n  np01:\n  - 1\n  - 2\n  - 3\n  np02:\n  - 1\n  - 2\n  - 3\n  np03:\n  - - 1.0\n    - 2.0\n    - 3.0\n  - - 4.0\n    - 5.0\n    - 6.0\n  p01: /tmp/yy\n  p02: null\n  p03: /xx/path\n  s01: xyz\n  s03: null\n  s04: default\n  s05: '77'\n  t01:\n  - 640\n  - 480\n  t02:\n  - 1\n  - '2'\n  t03:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  t04:\n  - 1\n  - 2\n  - 3\n  t05:\n  - key1\n  - key2\nbp02:\n  b03: null\n  b04: true\n  by01: null\n  by02: default\n  e01: red\n  e02: 200\n  f01: 0.5\n  f03: null\n  f04: 8.5\n  i01: 1\n  i03: null\n  l01: a\n  np01:\n  - 1\n  - 2\n  - 3\n  np02:\n  - 1\n  - 2\n  - 3\n  np03:\n  - - 1.0\n    - 2.0\n    - 3.0\n  - - 4.0\n    - 5.0\n    - 6.0\n  p01: /tmp/yy\n  p02: null\n  p03: /xx/path\n  s01: xyz\n  s03: null\n  s04: default\n  s05: '77'\n  t01:\n  - 640\n  - 480\n  t02:\n  - 1\n  - '2'\n  t03:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  t04:\n  - 1\n  - 2\n  - 3\n  t05:\n  - key1\n  - key2\nbp03: null\nby01: null\nby02: default\ne01: red\ne02: 200\nf01: 0.5\nf03: null\nf04: 8.5\ni01: 1\ni03: null\nl01: a\nnp01:\n- 1\n- 2\n- 3\nnp02:\n- 1\n- 2\n- 3\nnp03:\n- - 1.0\n  - 2.0\n  - 3.0\n- - 4.0\n  - 5.0\n  - 6.0\np01: /tmp/yy\np02: null\np03: /xx/path\ns01: xyz\ns03: null\ns04: default\ns05: '77'\nt01:\n- 640\n- 480\nt02:\n- 1\n- '2'\nt03:\n- - 1\n  - a\n- - 3.14\n  - b\nt04:\n- 1\n- 2\n- 3\nt05:\n- key1\n- key2\nxxx: 1\n"
