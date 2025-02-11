from typing import Any, Optional, Tuple, Union

import numpy as np
import pytest

from parametric import BaseParams


def test_error_ellipsis():
    class Test(BaseParams):
        x: ... = 1

    with pytest.raises(Exception) as exc_info:
        Test()
    assert "Ellipsis (`...`) is only allowed in this type format `tuple(x" in str(exc_info.value)


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
