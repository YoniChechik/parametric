import os
from tempfile import NamedTemporaryFile

from tests.conftest import MyParams


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


def _compare_strings_with_multiple_newlines(string1: str, string2: str) -> None:
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()

    for i, (line1, line2) in enumerate(zip(lines1, lines2)):
        assert line1 == line2, f"Difference at line {i+1}:\nString 1: {line1}\nString 2: {line2}"

    assert len(lines1) == len(lines2), "Not same amount of lines"


def test_to_dict(params: MyParams):
    params.freeze()

    params_dict = params.model_dump_serializable()
    assert params_dict["p04"] == "/xx/path"
