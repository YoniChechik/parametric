import sys
from enum import Enum, IntEnum

import pytest

if sys.version_info >= (3, 11):
    from enum import StrEnum

    has_str_enum = True
else:
    has_str_enum = False

from parametric import BaseParams


# Define Enums
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class StatusCode(IntEnum):
    SUCCESS = 200
    CLIENT_ERROR = 400
    SERVER_ERROR = 500


# Define MyParams class
class MyParams(BaseParams):
    color: Color = Color.RED
    status_code: StatusCode = StatusCode.SUCCESS


# Test case for to_dict method for Enum and IntEnum
def test_different_enums():
    params = MyParams()

    expected_dict = {
        "color": "green",
        "status_code": 500,
    }

    params.override_from_dict(expected_dict)

    assert params.color == Color.GREEN
    assert params.status_code == StatusCode.SERVER_ERROR


# Tests for StrEnum (only run on Python 3.11+)
@pytest.mark.skipif(not has_str_enum, reason="StrEnum only available from Python 3.11")
def test_strenum():
    class Role(StrEnum):
        ADMIN = "admin"
        USER = "user"
        GUEST = "guest"

    class MyStrEnumParamsParams(BaseParams):
        user_role: Role = Role.USER

    params = MyStrEnumParamsParams()

    expected_dict = {
        "user_role": "admin",
    }

    params.override_from_dict(expected_dict)

    assert params.user_role == Role.ADMIN


if __name__ == "__main__":
    pytest.main(["-v", __file__])
