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


def test_empty_field_error_on_freeze(params: MyParams):
    # Attempt to freeze with an unset mandatory field should raise an error
    with pytest.raises(Exception):
        params.freeze()


def test_change_after_freeze(params: MyParams):
    params.t03 = ((1, "c"), (3.14, "d"))

    # empty params to fill before freeze
    params.em01 = 123
    params.bp01.em01 = 456

    params.freeze()

    with pytest.raises(BaseException):
        params.t03 = ((2, "xxx"), (2, "xxx"))


if __name__ == "__main__":
    pytest.main(["--no-cov", "-v", __file__])
