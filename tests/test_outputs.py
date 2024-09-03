import os
from tempfile import NamedTemporaryFile

import pytest

from tests.conftest import MyParams


def test_save_yaml(params: MyParams):
    params.em01 = 123
    # TODO on freeze we dont get correct param name if below not set
    params.bp01.em01 = 456

    params.freeze()

    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    os.remove(tmp_yaml_name)

    expected_yaml = (
        "b03: null\n"
        "b04: true\n"
        "bp01:\n"
        "  b03: null\n"
        "  b04: true\n"
        "  by03: null\n"
        "  by04: b'default'\n"
        "  c03: null\n"
        "  c04: (1+2j)\n"
        "  c05: (3+4j)\n"
        "  em01: 456\n"
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
        f"  p04: {os.sep}xx{os.sep}path\n"
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
        "by04: b'default'\n"
        "c03: null\n"
        "c04: (1+2j)\n"
        "c05: (3+4j)\n"
        "em01: 123\n"
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
        f"p04: {os.sep}xx{os.sep}path\n"
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


def _compare_strings_with_multiple_newlines(string1: str, string2: str) -> None:
    lines1 = string1.splitlines()
    lines2 = string2.splitlines()

    for i, (line1, line2) in enumerate(zip(lines1, lines2)):
        if line1 != line2:
            raise Exception((f"Difference at line {i+1}:\nString 1: {line1}\nString 2: {line2}"))

    if len(lines1) != len(lines2):
        raise Exception("Not same amount of lines")


def test_to_dict(params: MyParams):
    params.em01 = 123
    # TODO on freeze we dont get correct param name if below not set
    params.bp01.em01 = 456

    params.freeze()

    params_dict = params.to_dict()
    assert params_dict["em01"] == 123


if __name__ == "__main__":
    pytest.main(["--no-cov", "-v", __file__])
