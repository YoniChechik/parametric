from enum import Enum, IntEnum, StrEnum

import pytest

from parametric import BaseScheme


# Define Enums
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class StatusCode(IntEnum):
    SUCCESS = 200
    CLIENT_ERROR = 400
    SERVER_ERROR = 500


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


# Define MyParamsScheme class
class MyParamsScheme(BaseScheme):
    color: Color = Color.RED
    status_code: StatusCode = StatusCode.SUCCESS
    user_role: Role = Role.USER


# Test case for to_dict method
def test_different_enums():
    params = MyParamsScheme()

    expected_dict = {
        "color": "green",
        "status_code": 500,
        "user_role": "admin",
    }

    params.override_from_dict(expected_dict)

    assert params.color == Color.GREEN
    assert params.status_code == StatusCode.SERVER_ERROR
    assert params.user_role == Role.ADMIN


if __name__ == "__main__":
    pytest.main(["-v", __file__])
