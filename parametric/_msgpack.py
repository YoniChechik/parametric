import abc
import datetime
import io
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union

NUMPY_AVAILABLE = False
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    pass

TORCH_AVAILABLE = False
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    pass

# Define type markers for all supported types
TYPE_NONE = bytes([0x00])
TYPE_BOOL_FALSE = bytes([0x01])
TYPE_BOOL_TRUE = bytes([0x02])
TYPE_INT = bytes([0x03])
TYPE_FLOAT = bytes([0x04])
TYPE_STR = bytes([0x05])
TYPE_LIST = bytes([0x06])
TYPE_TUPLE = bytes([0x07])
TYPE_DICT = bytes([0x08])
TYPE_NDARRAY = bytes([0x09])
TYPE_PATH = bytes([0x0A])
TYPE_DATETIME = bytes([0x0B])
TYPE_ENUM = bytes([0x0C])
TYPE_BASEPARAMS = bytes([0x0D])
TYPE_BYTES = bytes([0x0E])
TYPE_SET = bytes([0x0F])
TYPE_TORCH_TENSOR = bytes([0x10])


class _AbstractType(abc.ABC):
    def __init__(self):
        raise TypeError(f"Cannot instantiate abstract class {self.__class__.__name__}")

    @classmethod
    @abc.abstractmethod
    def pack(cls, obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        """Pack the object into the stream."""
        raise NotImplementedError(f"Abstract method {cls.pack.__name__}() must be implemented in derived class")

    @classmethod
    @abc.abstractmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> Any:
        """Unpack an object from the stream given the type marker."""
        raise NotImplementedError(f"Abstract method {cls.unpack.__name__}() must be implemented in derived class")

    @classmethod
    @abc.abstractmethod
    def is_ext(cls, marker: bytes) -> bool:
        """Return True if this type is an extension type of the relevant class."""
        raise NotImplementedError(f"Abstract method {cls.is_ext.__name__}() must be implemented in derived class")


# Already implemented types
class _NoneType(_AbstractType):
    MARKER = TYPE_NONE

    @classmethod
    def pack(cls, obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> None:
        return None

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _BoolType(_AbstractType):
    MARKER_TRUE = TYPE_BOOL_TRUE
    MARKER_FALSE = TYPE_BOOL_FALSE

    @classmethod
    def pack(cls, obj: bool, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER_TRUE if obj else cls.MARKER_FALSE)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> bool:
        return marker == cls.MARKER_TRUE

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker in (cls.MARKER_TRUE, cls.MARKER_FALSE)


class _IntType(_AbstractType):
    MARKER = TYPE_INT

    @classmethod
    def pack(cls, obj: int, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">q", obj))

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> int:
        data = stream.read(8)
        return struct.unpack(">q", data)[0]

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _FloatType(_AbstractType):
    MARKER = TYPE_FLOAT

    @classmethod
    def pack(cls, obj: float, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">d", obj))

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> float:
        data = stream.read(8)
        return struct.unpack(">d", data)[0]

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _StringType(_AbstractType):
    MARKER = TYPE_STR

    @classmethod
    def pack(cls, obj: str, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        encoded = obj.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded)))
        stream.write(encoded)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> str:
        length = struct.unpack(">I", stream.read(4))[0]
        data = stream.read(length)
        return data.decode("utf-8")

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _ListType(_AbstractType):
    MARKER = TYPE_LIST

    @classmethod
    def pack(cls, obj: list, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">I", len(obj)))
        for item in obj:
            pack_obj(item, stream)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> list:
        length = struct.unpack(">I", stream.read(4))[0]
        return [unpack_obj(stream) for _ in range(length)]

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _TupleType(_AbstractType):
    MARKER = TYPE_TUPLE

    @classmethod
    def pack(cls, obj: tuple, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">I", len(obj)))
        for item in obj:
            pack_obj(item, stream)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> tuple:
        length = struct.unpack(">I", stream.read(4))[0]
        return tuple(unpack_obj(stream) for _ in range(length))

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _DictType(_AbstractType):
    MARKER = TYPE_DICT

    @classmethod
    def pack(cls, obj: dict, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">I", len(obj)))
        for key, value in obj.items():
            pack_obj(key, stream)
            pack_obj(value, stream)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> dict:
        length = struct.unpack(">I", stream.read(4))[0]
        result = {}
        for _ in range(length):
            key = unpack_obj(stream)
            value = unpack_obj(stream)
            result[key] = value
        return result

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


# --- New type classes ---


class _NDArrayType(_AbstractType):
    MARKER = TYPE_NDARRAY

    @classmethod
    def pack(cls, obj: np.ndarray, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        # Store dtype information
        dtype_str = obj.dtype.str
        encoded_dtype = dtype_str.encode("utf-8")
        stream.write(struct.pack(">B", len(encoded_dtype)))
        stream.write(encoded_dtype)
        # Store shape information
        stream.write(struct.pack(">B", len(obj.shape)))
        stream.write(struct.pack(f">{len(obj.shape)}I", *obj.shape))
        # Write raw data (assumes a contiguous memory layout)
        stream.write(obj.data)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> Any:
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required to deserialize ndarray objects")
        dtype_length = struct.unpack(">B", stream.read(1))[0]
        dtype_str = stream.read(dtype_length).decode("utf-8")
        ndim = struct.unpack(">B", stream.read(1))[0]
        shape = struct.unpack(f">{ndim}I", stream.read(4 * ndim))
        dtype = np.dtype(dtype_str)
        data_length = dtype.itemsize * int(np.prod(shape))
        data = stream.read(data_length)
        arr = np.frombuffer(data, dtype=dtype).reshape(shape)
        return arr

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _PathType(_AbstractType):
    MARKER = TYPE_PATH

    @classmethod
    def pack(cls, obj: Path, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        path_str = obj.as_posix()
        encoded = path_str.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded)))
        stream.write(encoded)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> Path:
        length = struct.unpack(">I", stream.read(4))[0]
        data = stream.read(length)
        return Path(data.decode("utf-8"))

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _DateTimeType(_AbstractType):
    MARKER = TYPE_DATETIME

    @classmethod
    def pack(cls, obj: datetime.datetime, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        timestamp = obj.timestamp()
        stream.write(struct.pack(">d", timestamp))

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> datetime.datetime:
        data = stream.read(8)
        timestamp = struct.unpack(">d", data)[0]
        return datetime.datetime.fromtimestamp(timestamp)

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


@dataclass
class EnumData:
    class_name: str
    value_name: str


class _EnumType(_AbstractType):
    MARKER = TYPE_ENUM

    @classmethod
    def pack(cls, obj: Enum, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        class_name = obj.__class__.__name__
        value_name = obj.name
        encoded_class = class_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_class)))
        stream.write(encoded_class)
        encoded_name = value_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_name)))
        stream.write(encoded_name)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> EnumData:
        class_len = struct.unpack(">I", stream.read(4))[0]
        class_name = stream.read(class_len).decode("utf-8")
        value_len = struct.unpack(">I", stream.read(4))[0]
        value_name = stream.read(value_len).decode("utf-8")
        return EnumData(class_name=class_name, value_name=value_name)

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


@dataclass
class BaseParamsData:
    class_name: str
    param_dict: dict


class _BaseParamsType(_AbstractType):
    MARKER = TYPE_BASEPARAMS

    @classmethod
    def pack(cls, obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        # 'BaseParams' is assumed to have a method to_dict(recursive=False)
        stream.write(cls.MARKER)
        class_name = obj.__class__.__name__
        encoded_class = class_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_class)))
        stream.write(encoded_class)
        # Pack the parameters dictionary
        pack_obj(obj.to_dict(recursive=False), stream)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> BaseParamsData:
        class_len = struct.unpack(">I", stream.read(4))[0]
        class_name = stream.read(class_len).decode("utf-8")
        param_dict = unpack_obj(stream)
        return BaseParamsData(class_name=class_name, param_dict=param_dict)

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _BytesType(_AbstractType):
    MARKER = TYPE_BYTES

    @classmethod
    def pack(cls, obj: bytes, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">I", len(obj)))
        stream.write(obj)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> bytes:
        length = struct.unpack(">I", stream.read(4))[0]
        return stream.read(length)

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _SetType(_AbstractType):
    MARKER = TYPE_SET

    @classmethod
    def pack(cls, obj: set, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        stream.write(struct.pack(">I", len(obj)))
        for item in obj:
            pack_obj(item, stream)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> set:
        (length,) = struct.unpack(">I", stream.read(4))
        result_set = set()
        for _ in range(length):
            result_set.add(unpack_obj(stream))
        return result_set

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


class _TorchTensorType(_AbstractType):
    MARKER = TYPE_TORCH_TENSOR

    @classmethod
    def pack(cls, obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
        stream.write(cls.MARKER)
        # Store dtype information (e.g., "torch.float32")
        dtype_str = str(obj.dtype)
        encoded_dtype = dtype_str.encode("utf-8")
        stream.write(struct.pack(">B", len(encoded_dtype)))
        stream.write(encoded_dtype)
        # Store shape
        stream.write(struct.pack(">B", len(obj.shape)))
        stream.write(struct.pack(f">{len(obj.shape)}I", *obj.shape))
        # Write the tensor data by converting to a numpy memoryview
        numpy_data = obj.cpu().numpy().data
        stream.write(numpy_data)

    @classmethod
    def unpack(cls, stream: io.IOBase, marker: bytes) -> Any:
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required to deserialize tensor objects")
        dtype_length = struct.unpack(">B", stream.read(1))[0]
        dtype_str = stream.read(dtype_length).decode("utf-8")
        # Extract the basic dtype string (assumes format like "torch.float32")
        dtype = np.dtype(dtype_str.split(".")[-1])
        ndim = struct.unpack(">B", stream.read(1))[0]
        shape = struct.unpack(f">{ndim}I", stream.read(4 * ndim))
        data_length = int(np.prod(shape)) * dtype.itemsize
        data = stream.read(data_length)
        # Create a writable numpy array from the data
        data_array = np.frombuffer(data, dtype=dtype).copy()
        tensor = torch.from_numpy(data_array)
        return tensor

    @classmethod
    def is_ext(cls, marker: bytes) -> bool:
        return marker == cls.MARKER


# --- Refactored helper functions ---


def pack_obj(obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
    """Recursively pack an object to the stream using the appropriate type class."""
    # avoid circular import; BaseParams is expected to be defined elsewhere
    from parametric import BaseParams  # type: ignore

    if obj is None:
        _NoneType.pack(obj, stream)
    elif isinstance(obj, bool):
        _BoolType.pack(obj, stream)
    elif isinstance(obj, int):
        _IntType.pack(obj, stream)
    elif isinstance(obj, float):
        _FloatType.pack(obj, stream)
    elif isinstance(obj, str):
        _StringType.pack(obj, stream)
    elif isinstance(obj, list):
        _ListType.pack(obj, stream)
    elif isinstance(obj, tuple):
        _TupleType.pack(obj, stream)
    elif isinstance(obj, dict):
        _DictType.pack(obj, stream)
    elif NUMPY_AVAILABLE and isinstance(obj, np.ndarray):
        _NDArrayType.pack(obj, stream)
    elif isinstance(obj, Path):
        _PathType.pack(obj, stream)
    elif isinstance(obj, datetime.datetime):
        _DateTimeType.pack(obj, stream)
    elif isinstance(obj, Enum):
        _EnumType.pack(obj, stream)
    elif isinstance(obj, BaseParams):
        _BaseParamsType.pack(obj, stream)
    elif isinstance(obj, bytes):
        _BytesType.pack(obj, stream)
    elif isinstance(obj, set):
        _SetType.pack(obj, stream)
    elif TORCH_AVAILABLE and isinstance(obj, torch.Tensor):
        _TorchTensorType.pack(obj, stream)
    else:
        raise TypeError(f"Unsupported type: {type(obj)}")


def unpack_obj(stream: io.IOBase) -> Any:
    """Recursively unpack an object from the stream by delegating to the correct type class."""
    type_marker = stream.read(1)
    if not type_marker:
        raise EOFError("Unexpected end of stream")

    for cls in (
        _NoneType,
        _BoolType,
        _IntType,
        _FloatType,
        _StringType,
        _ListType,
        _TupleType,
        _DictType,
        _NDArrayType,
        _PathType,
        _DateTimeType,
        _EnumType,
        _BytesType,
        _SetType,
        _TorchTensorType,
        # MUST be last
        _BaseParamsType,
    ):
        if cls.is_ext(type_marker):
            return cls.unpack(stream, type_marker)
    raise ValueError(f"Unknown type marker: {type_marker}")
