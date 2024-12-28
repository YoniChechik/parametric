from typing import Any, Optional, Tuple, Union

import numpy as np
import pytest

from parametric import BaseParams
from tests.conftest import MyParams


def test_invalid_overrides(params: MyParams):
    # Attempt to override with invalid type should raise an error
    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": ((1, "a"), "not a tuple")})
    assert "Value error, In t03, <class 'str'> is not tuple compatible." in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t03": (("not an int", "a"), (3.14, "b"))})
    assert "Input should be a valid integer, unable to parse string as an integer" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"t04": "not a tuple"})
    assert "Value error, In t04, <class 'str'> is not tuple compatible." in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"i01": "not an int or float"})
    assert "Input should be a valid integer, unable to parse string as an integer" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"non_existent_param": 123})
    assert "Object has no attribute 'non_existent_param'" in str(exc_info.value)


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
    assert "Type of t cannot be 'tuple' without specifying element types" in str(exc_info.value)

    class Test3(BaseParams):
        t: tuple[tuple] = ((1, 2, 3),)

    with pytest.raises(Exception) as exc_info:
        Test3()
    assert "Type of t cannot be 'tuple' without specifying element types" in str(exc_info.value)


def test_error_np_array_type():
    class Test(BaseParams):
        array_param: np.array = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type of array_param cannot be 'np.array'. Try np.ndarray[int] instead" in str(exc_info.value)


def test_error_np_ndarray_no_inner_arg():
    class Test(BaseParams):
        array_param: np.ndarray = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type of array_param cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])" in str(
        exc_info.value
    )


def test_error_np_ndarray_multiple_inner_arg():
    class Test(BaseParams):
        array_param: np.ndarray[int, float] = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "dtype of 'np.ndarray' array_param should have exactly 1 inner args (e.g. np.ndarray[int])" in str(
        exc_info.value
    )


def test_error_Any_type():
    class Test(BaseParams):
        array_param: Any = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type `Any` is not allowed, cannot convert 'array_param'" in str(exc_info.value)


def test_old_types_error():
    class Test(BaseParams):
        array_param: Tuple[int, int] = (1, 2)

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Old Tuple[x,y,z] type is bad practice. Use tuple[x,y,z] instead." in str(exc_info.value)

    class Test2(BaseParams):
        array_param: Union[int, float] = 1

    with pytest.raises(Exception) as exc_info:
        Test2()
    assert "Old Union[x,y,z] type is bad practice. Use x | y | z instead." in str(exc_info.value)

    class Test3(BaseParams):
        array_param: Optional[int] = 1

    with pytest.raises(Exception) as exc_info:
        Test3()
    assert "Old Optional[x] type is bad practice. Use x | None instead." in str(exc_info.value)
