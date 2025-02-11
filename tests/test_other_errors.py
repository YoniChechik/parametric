import pytest

from parametric import BaseParams


def test_error_initialize_base_params():
    with pytest.raises(Exception) as exc_info:
        BaseParams()
    assert "BaseParams cannot be instantiated directly" in str(exc_info.value)


def test_error_non_existent_param():
    class Test(BaseParams):
        param: int = 1

    t = Test()
    with pytest.raises(Exception) as exc_info:
        t.non_existent_param = 123
    assert "`non_existent_param` is not a valid field in Test" in str(exc_info.value)
