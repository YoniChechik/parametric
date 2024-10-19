from typing import Tuple

import pytest

from parametric._base_params import BaseParams
from tests.conftest import MyParams


def test_invalid_overrides(params: MyParams):
    # Attempt to override with invalid type should raise an error
    with pytest.raises(Exception):
        params.override_from_dict({"nested_tuple": ((1, "a"), "not a tuple")})

    with pytest.raises(Exception):
        params.override_from_dict({"nested_tuple": (("not an int", "a"), (3.14, "b"))})

    with pytest.raises(Exception):
        params.override_from_dict({"optional_tuple": "not a tuple"})

    with pytest.raises(Exception):
        params.override_from_dict({"union_field": "not an int or float"})


def test_to_dict_without_freeze():
    params = MyParamsNew()

    # Attempt to call to_dict without freezing should raise an error
    with pytest.raises(RuntimeError):
        params.to_dict()


def test_empty_field_error_on_freeze():
    class CustomParamsScheme(BaseParams):
        mandatory_field: int

    params = CustomParamsScheme()

    # Attempt to freeze with an unset mandatory field should raise an error
    with pytest.raises(Exception):
        params.freeze()


def test_change_after_freeze():
    params = MyParamsNew()
    params.nested_tuple = ((1, "c"), (3.14, "d"))

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
