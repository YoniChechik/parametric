from typing import Any, Tuple, Union

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
        params.override_from_dict({"i04": "not an int or float"})
    assert "Input should be a valid integer, unable to parse string as an integer" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.override_from_dict({"non_existent_param": 123})
    assert "Object has no attribute 'non_existent_param'" in str(exc_info.value)


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


def test_error_np_array_typehint():
    class Test(BaseParams):
        array_param: np.array = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type hint for array_param cannot be 'np.array'. Try np.ndarray[int] instead" in str(exc_info.value)


def test_error_np_ndarray_no_inner_arg():
    class Test(BaseParams):
        array_param: np.ndarray = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert (
        "Type hint for array_param cannot be 'np.ndarray' without specifying element types (e.g. np.ndarray[int])"
        in str(exc_info.value)
    )


def test_error_np_ndarray_multiple_inner_arg():
    class Test(BaseParams):
        array_param: np.ndarray[int, float] = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type hint for 'np.ndarray' array_param should have exactly 1 inner args (e.g. np.ndarray[int])" in str(
        exc_info.value
    )


def test_error_Any_typehint():
    class Test(BaseParams):
        array_param: Any = np.array([1, 2, 3])

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type `Any` is not allowed, cannot convert 'array_param'" in str(exc_info.value)


def test_error_non_existent_param(params: MyParams):
    class Test(BaseParams):
        array_param: int = 1

    t = Test()
    with pytest.raises(Exception) as exc_info:
        t.non_existent_param = 123
    assert "Can't define parameter non_existent_param after initialization" in str(exc_info.value)


def test_error_Union_no_inner_args(params: MyParams):
    class Test(BaseParams):
        array_param: Union = 1  # type: ignore

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Type hint for array_param cannot be 'Union' without specifying element types (e.g. Union[int, str])" in str(
        exc_info.value
    )


def test_error_changing_frozen_np_array():
    class Test(BaseParams):
        array_param: np.ndarray[int] = np.array([1, 2, 3])

    t = Test()

    # can't change frozen np.array
    with pytest.raises(Exception) as exc_info:
        t.array_param[0] = 123
    assert "assignment destination is read-only" in str(exc_info.value)

    # still reference the same object
    tt = np.asarray(t.array_param)
    with pytest.raises(Exception) as exc_info:
        tt[0] = 123
    assert "assignment destination is read-only" in str(exc_info.value)

    # copy the object- now we can change it
    tt = np.copy(t.array_param)
    tt[0] = 123

    tt = np.array(t.array_param)
    tt[0] = 123
