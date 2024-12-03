from typing import Tuple

import pytest

from parametric._base_params import BaseParams
from tests.conftest import MyParams


def test_invalid_overrides(params: MyParams):
    # Attempt to override with invalid type should raise an error
    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": ((1, "a"), "not a tuple")})
    assert "Type coercion error" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": (("not an int", "a"), (3.14, "b"))})
    assert "Type coercion error" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t04": "not a tuple"})
    assert "Type coercion error" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"i04": "not an int or float"})
    assert "Type coercion error" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"non_existent_param": 123})
    assert "Parameter name 'non_existent_param' does not exist" in str(exc_info.value)


def test_error_change_directly(params: MyParams):
    with pytest.raises(Exception) as exc_info:
        params.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.bp01.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)


def test_error_mutable_field():
    class Test(BaseParams):
        list_param: list[int] = [1, 2, 3]

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Parameter 'list_param' must be one of the following" in str(exc_info.value)


def test_error_tuple_no_inner_args():
    class Test(BaseParams):
        t: tuple = (1, 2, 3)

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type hint for t cannot be 'tuple' without specifying element types" in str(exc_info.value)

    class Test2(BaseParams):
        t: Tuple = (1, 2, 3)

    with pytest.raises(Exception) as exc_info:
        Test2()
    assert "Type hint for t cannot be 'Tuple' without specifying element types" in str(exc_info.value)

    class Test3(BaseParams):
        t: tuple[tuple] = ((1, 2, 3),)

    with pytest.raises(Exception) as exc_info:
        Test3()
    assert "Type hint for t cannot be 'tuple' without specifying element types" in str(exc_info.value)


def test_error_initialize_base_params():
    with pytest.raises(Exception) as exc_info:
        BaseParams()
    assert "BaseParams cannot be instantiated directly" in str(exc_info.value)
