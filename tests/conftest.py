"""
specific file name that we can build fixtures and use them in all other test files for pytest
"""

import warnings
from enum import Enum
from pathlib import Path
from typing import Literal

import numpy as np
import pytest

from parametric import BaseParams

warnings.filterwarnings("error")


# Define Enums
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class StatusCode(Enum):
    SUCCESS = 200
    CLIENT_ERROR = 400
    SERVER_ERROR = 500


class A(BaseParams):
    np01: np.ndarray[int] = np.array([1, 2, 3])
    np02: np.ndarray[int] = [1, 2, 3]
    np03: np.ndarray[int] = [[1, 2, 3], [4, 5, 6]]
    np04: np.ndarray[int] | None = [[1, 2, 3], [4, 5, 6]]

    # For int
    i01: int = 1
    i03: int | None = None

    # For str
    s01: str = "xyz"
    s03: str | None = None
    s04: str = "default"
    s05: str = "77"

    # For float
    f01: float = 0.5
    f03: float | None = None
    f04: float = 8.5

    # For bool
    b03: bool | None = None
    b04: bool = True

    # For bytes
    by01: bytes | None = None
    by02: bytes = b"default"
    # by03: bytes = "default"  # string

    # For Path
    p01: Path = "/tmp/yy"
    p02: Path | None = None
    p03: Path = Path("/xx/path")

    # literals
    l01: Literal["a", "b", "c"] = "a"

    # tuples
    t01: tuple[int, int] = (640, 480)
    t02: tuple[int, str] = (1, "2")
    t03: tuple[tuple[int, str], tuple[float, str]] = ((1, "a"), (3.14, "b"))
    t04: tuple[int, int, int] | None = (1, 2, 3)
    t05: tuple[str, ...] = ("key1", "key2")
    t06: tuple[np.ndarray[int], Path] = ([[1, 2, 3], [4, 5, 6]], "/x/y")

    # enums
    e01: Color = Color.RED
    e02: StatusCode = StatusCode.SUCCESS


class B(A):
    """
    all fields from above are fields here + a complex field that also has all
    """

    bp01: A = A()
    bp02: A | None = A()
    bp03: A | None = None


class MyParams(B):
    xxx: int = 1


@pytest.fixture(scope="function")  # generate new instance for each test function
def params():
    x = MyParams()
    return x
