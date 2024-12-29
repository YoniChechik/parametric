import numpy as np
import pytest

from parametric import BaseParams
from tests.conftest import MyParams


def test_error_change_directly(params: MyParams):
    with pytest.raises(Exception) as exc_info:
        params.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        params.bp01.t03 = ((2, "xxx"), (2, "xxx"))
    assert "Instance is frozen" in str(exc_info.value)


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
