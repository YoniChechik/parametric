import numpy as np
import pytest

from parametric import Override
from tests.conftest import MyParams


def test_override_context(params: MyParams):
    with Override():
        params.f04 = 0.001
        params.np01 = [1, 2]
        params.bp01.i01 = 10000

    assert params.f04 == 0.001
    assert np.array_equal(params.np01, [1, 2])
    assert params.bp01.i01 == 10000

    with pytest.raises(Exception) as exc_info:
        params.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)


def test_override_context_with_override_from_dict(params: MyParams):
    with Override():
        params.override_from_dict({"f04": 0.001, "np01": [1, 2], "bp01": {"i01": 10000}})

    assert params.f04 == 0.001
    assert np.array_equal(params.np01, [1, 2])
    assert params.bp01.i01 == 10000

    with pytest.raises(Exception) as exc_info:
        params.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)
