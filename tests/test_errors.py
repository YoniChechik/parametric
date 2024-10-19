from typing import Tuple

import pytest

from parametric._base_params import BaseParams
from tests.conftest import MyParams


def test_invalid_overrides(params: MyParams):
    # Attempt to override with invalid type should raise an error
    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": ((1, "a"), "not a tuple")})
    assert "t03.1\n  Input should be a valid tuple [type=tuple_type, input_value='not a tuple', input_type=str]" in str(
        exc_info.value
    )

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": (("not an int", "a"), (3.14, "b"))})
    assert (
        "t03.0.0\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='not an int', input_type=str]"
        in str(exc_info.value)
    )

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t04": "not a tuple"})
    assert "t04\n  Input should be a valid tuple [type=tuple_type, input_value='not a tuple', input_type=str]" in str(
        exc_info.value
    )

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"i04": "not an int or float"})
    assert (
        "i04.int\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='not an int or float', input_type=str]"
        in str(exc_info.value)
    )
    assert (
        "i04.float\n  Input should be a valid number, unable to parse string as a number [type=float_parsing, input_value='not an int or float', input_type=str]"
        in str(exc_info.value)
    )


def test_error_change_after_freeze(params: MyParams):
    params.t03 = ((1, "c"), (3.14, "d"))

    params.freeze()

    with pytest.raises(Exception) as exc_info:
        params.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.bp01.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.bp01.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)


def test_error_mutable_field():
    class Test(BaseParams):
        list_param: list[int] = [1, 2, 3]

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "typehint list[int] is not allowed because it is not immutable" in str(exc_info.value)


def test_error_tuple_no_inner_args():
    class Test(BaseParams):
        t: tuple = (1, 2, 3)

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "In t, must declere args for tuple typehint, e.g. tuple[int]" in str(exc_info.value)

    class Test2(BaseParams):
        t: Tuple = (1, 2, 3)

    with pytest.raises(Exception) as exc_info:
        Test2()
    assert "In t, must declere args for tuple typehint, e.g. tuple[int]" in str(exc_info.value)

    class Test3(BaseParams):
        t: tuple[tuple] = ((1, 2, 3),)

    with pytest.raises(Exception) as exc_info:
        Test3()
    assert "In t, must declere args for tuple typehint, e.g. tuple[int]" in str(exc_info.value)
