import pytest

from tests.conftest import MyParams


def test_invalid_overrides(params: MyParams):
    # Attempt to override with invalid type should raise an error
    with pytest.raises(Exception):
        params.override_from_dict({"t03": ((1, "a"), "not a tuple")})

    with pytest.raises(Exception):
        params.override_from_dict({"t03": (("not an int", "a"), (3.14, "b"))})

    with pytest.raises(Exception):
        params.override_from_dict({"t04": "not a tuple"})

    with pytest.raises(Exception):
        params.override_from_dict({"i04": "not an int or float"})


def test_change_after_freeze(params: MyParams):
    params.t03 = ((1, "c"), (3.14, "d"))

    params.freeze()

    with pytest.raises(Exception):
        params.t03 = ((2, "xxx"), (2, "xxx"))

    with pytest.raises(Exception):
        params.bp01.t03 = ((2, "xxx"), (2, "xxx"))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
