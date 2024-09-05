from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ConversionFromType(Enum):
    PYTHON_OBJECT = "python_object"
    DUMPABLE = "dumpable"
    STR = "str"


class AbstractBaseParams(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def override_from_dict(self, changed_params: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def _override_from_dict(self, changed_params: dict[str, Any], conversion_from_type: ConversionFromType) -> None:
        pass
