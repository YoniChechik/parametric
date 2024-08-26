from abc import ABC, abstractmethod
from typing import Any


class AbstractBaseParams(ABC):
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def override_from_dict(self, changed_params: dict[str, Any]) -> None:
        pass
