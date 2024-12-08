import os
from tempfile import NamedTemporaryFile

from tests.conftest import MyParams


def test_save_yaml(params: MyParams):
    with NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp_yaml:
        tmp_yaml_name = tmp_yaml.name
        params.save_yaml(tmp_yaml_name)

    with open(tmp_yaml_name) as f:
        loaded_params = f.read()

    expected_yaml = "b03: null\nb04: true\nbp01:\n  b03: null\n  b04: true\n  by01: null\n  by02: default\n  e01: red\n  e02: 200\n  f01: 0.5\n  f03: null\n  f04: 8.5\n  i01: 1\n  i03: null\n  i04: 8\n  i05: 9\n  l01: a\n  np01:\n  - 1\n  - 2\n  - 3\n  np02:\n  - 1\n  - 2\n  - 3\n  np03:\n  - - 1.0\n    - 2.0\n    - 3.0\n  - - 4.0\n    - 5.0\n    - 6.0\n  o01:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  o02:\n  - 1\n  - 2\n  - 3\n  o03: 42\n  o04:\n  - key1\n  - 1\n  p01: /tmp/yy\n  p02: null\n  p03: /xx/path\n  s01: xyz\n  s03: null\n  s04: default\n  s05: '77'\n  t01:\n  - 640\n  - 480\n  t02:\n  - 1\n  - '2'\n  t03:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  t04:\n  - 1\n  - 2\n  - 3\n  t05:\n  - key1\n  - 1\nbp02:\n  b03: null\n  b04: true\n  by01: null\n  by02: default\n  e01: red\n  e02: 200\n  f01: 0.5\n  f03: null\n  f04: 8.5\n  i01: 1\n  i03: null\n  i04: 8\n  i05: 9\n  l01: a\n  np01:\n  - 1\n  - 2\n  - 3\n  np02:\n  - 1\n  - 2\n  - 3\n  np03:\n  - - 1.0\n    - 2.0\n    - 3.0\n  - - 4.0\n    - 5.0\n    - 6.0\n  o01:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  o02:\n  - 1\n  - 2\n  - 3\n  o03: 42\n  o04:\n  - key1\n  - 1\n  p01: /tmp/yy\n  p02: null\n  p03: /xx/path\n  s01: xyz\n  s03: null\n  s04: default\n  s05: '77'\n  t01:\n  - 640\n  - 480\n  t02:\n  - 1\n  - '2'\n  t03:\n  - - 1\n    - a\n  - - 3.14\n    - b\n  t04:\n  - 1\n  - 2\n  - 3\n  t05:\n  - key1\n  - 1\nbp03: null\nby01: null\nby02: default\ne01: red\ne02: 200\nf01: 0.5\nf03: null\nf04: 8.5\ni01: 1\ni03: null\ni04: 8\ni05: 9\nl01: a\nnp01:\n- 1\n- 2\n- 3\nnp02:\n- 1\n- 2\n- 3\nnp03:\n- - 1.0\n  - 2.0\n  - 3.0\n- - 4.0\n  - 5.0\n  - 6.0\no01:\n- - 1\n  - a\n- - 3.14\n  - b\no02:\n- 1\n- 2\n- 3\no03: 42\no04:\n- key1\n- 1\np01: /tmp/yy\np02: null\np03: /xx/path\ns01: xyz\ns03: null\ns04: default\ns05: '77'\nt01:\n- 640\n- 480\nt02:\n- 1\n- '2'\nt03:\n- - 1\n  - a\n- - 3.14\n  - b\nt04:\n- 1\n- 2\n- 3\nt05:\n- key1\n- 1\nxxx: 1\n"

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
    params_dict = params.to_dumpable_dict()
    assert params_dict["p03"] == "/xx/path"
