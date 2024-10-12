import os
from tempfile import NamedTemporaryFile

import pytest

from tests.conftest import MyParams


def test_save_yaml(params: MyParams):
    params.freeze()

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    expected_yaml = (
        "b03: null\n"
        "b04: true\n"
        "bp01:\n"
        "  b03: null\n"
        "  b04: true\n"
        "  by03: null\n"
        "  by04: default\n"
        "  f01: 0.5\n"
        "  f03: null\n"
        "  f04: 8.5\n"
        "  i01: 1\n"
        "  i03: null\n"
        "  i04: 8\n"
        "  i05: 9\n"
        "  l01: a\n"
        "  o01:\n"
        "  - - 1\n"
        "    - a\n"
        "  - - 3.14\n"
        "    - b\n"
        "  o02:\n"
        "  - 1\n"
        "  - 2\n"
        "  - 3\n"
        "  o03: 42\n"
        "  o04:\n"
        "  - key1\n"
        "  - 1\n"
        "  p03: null\n"
        "  p04: /xx/path\n"
        "  s01: xyz\n"
        "  s03: null\n"
        "  s04: default\n"
        "  s05: '77'\n"
        "  t01:\n"
        "  - 640\n"
        "  - 480\n"
        "  t02:\n"
        "  - 1\n"
        "  - '2'\n"
        "  t03:\n"
        "  - - 1\n"
        "    - a\n"
        "  - - 3.14\n"
        "    - b\n"
        "  t04:\n"
        "  - 1\n"
        "  - 2\n"
        "  - 3\n"
        "  t05:\n"
        "  - key1\n"
        "  - 1\n"
        "by03: null\n"
        "by04: default\n"
        "f01: 0.5\n"
        "f03: null\n"
        "f04: 8.5\n"
        "i01: 1\n"
        "i03: null\n"
        "i04: 8\n"
        "i05: 9\n"
        "l01: a\n"
        "o01:\n"
        "- - 1\n"
        "  - a\n"
        "- - 3.14\n"
        "  - b\n"
        "o02:\n"
        "- 1\n"
        "- 2\n"
        "- 3\n"
        "o03: 42\n"
        "o04:\n"
        "- key1\n"
        "- 1\n"
        "p03: null\n"
        "p04: /xx/path\n"
        "s01: xyz\n"
        "s03: null\n"
        "s04: default\n"
        "s05: '77'\n"
        "t01:\n"
        "- 640\n"
        "- 480\n"
        "t02:\n"
        "- 1\n"
        "- '2'\n"
        "t03:\n"
        "- - 1\n"
        "  - a\n"
        "- - 3.14\n"
        "  - b\n"
        "t04:\n"
        "- 1\n"
        "- 2\n"
        "- 3\n"
        "t05:\n"
        "- key1\n"
        "- 1\n"
    )

    _compare_strings_with_multiple_newlines(loaded_params, expected_yaml)

    params2 = MyParams()
    params2.override_from_yaml_file(tmp_yaml_name)

    os.remove(tmp_yaml_name)
    assert params == params2


def _compare_strings_with_multiple_newlines(string1: str, string2: str) -> None:
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()

    for i, (line1, line2) in enumerate(zip(lines1, lines2)):
        if line1 != line2:
            raise Exception((f"Difference at line {i+1}:\nString 1: {line1}\nString 2: {line2}"))

    if len(lines1) != len(lines2):
        raise Exception("Not same amount of lines")


def test_to_dict(params: MyParams):
    params.freeze()

    params_dict = params.model_dump_serializable()
    assert params_dict["p04"] == "/xx/path"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
