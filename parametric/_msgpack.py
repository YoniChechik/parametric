import datetime
import io
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union

import numpy as np

# -- Type markers (1 byte each) --
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
TYPE_ENUM = bytes([0x0C])  # New type marker for Enum
TYPE_BASEPARAMS = bytes([0x0D])  # New type marker for BaseParams
TYPE_BYTES = bytes([0x0E])  # New type marker for bytes objects
TYPE_SET = bytes([0x0F])  # New type marker for sets
# -- Serialization functions --


def pack_obj(obj: Any, stream: Union[io.BytesIO, io.BufferedWriter]) -> None:
    """Recursively pack an object to the stream with headers and length prefixes."""
    # avoid circular import
    from parametric import BaseParams

    if obj is None:
        stream.write(TYPE_NONE)
    elif isinstance(obj, bool):
        stream.write(TYPE_BOOL_TRUE if obj else TYPE_BOOL_FALSE)
    elif isinstance(obj, int):
        stream.write(TYPE_INT)
        stream.write(struct.pack(">q", obj))  # 8-byte big-endian integer
    elif isinstance(obj, float):
        stream.write(TYPE_FLOAT)
        stream.write(struct.pack(">d", obj))  # 8-byte float (double)
    elif isinstance(obj, str):
        stream.write(TYPE_STR)
        encoded = obj.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded)))  # 4-byte length
        stream.write(encoded)
    elif isinstance(obj, list):
        stream.write(TYPE_LIST)
        stream.write(struct.pack(">I", len(obj)))  # number of elements
        for item in obj:
            pack_obj(item, stream)
    elif isinstance(obj, tuple):
        stream.write(TYPE_TUPLE)
        stream.write(struct.pack(">I", len(obj)))
        for item in obj:
            pack_obj(item, stream)
    elif isinstance(obj, dict):
        stream.write(TYPE_DICT)
        stream.write(struct.pack(">I", len(obj)))  # number of key-value pairs
        for key, value in obj.items():
            pack_obj(key, stream)
            pack_obj(value, stream)
    elif isinstance(obj, np.ndarray):
        stream.write(TYPE_NDARRAY)
        # Optimize dtype storage - store only the basic dtype string
        dtype_str = obj.dtype.str
        encoded_dtype = dtype_str.encode("utf-8")
        stream.write(struct.pack(">B", len(encoded_dtype)))  # Use 1 byte for dtype length
        stream.write(encoded_dtype)
        # Optimize shape storage
        stream.write(struct.pack(">B", len(obj.shape)))  # Use 1 byte for ndim
        stream.write(struct.pack(f">{len(obj.shape)}I", *obj.shape))  # Pack all dims at once
        # Write data directly using a memoryview for zero-copy access
        stream.write(obj.data)  # obj.data is a memoryview
    elif isinstance(obj, Path):
        stream.write(TYPE_PATH)
        path_str = obj.as_posix()
        encoded = path_str.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded)))
        stream.write(encoded)
    elif isinstance(obj, datetime.datetime):
        stream.write(TYPE_DATETIME)
        # Save datetime as a timestamp (8-byte float)
        timestamp = obj.timestamp()
        stream.write(struct.pack(">d", timestamp))
    elif isinstance(obj, Enum):
        stream.write(TYPE_ENUM)
        # Store the enum class name and value name
        class_name = obj.__class__.__name__
        value_name = obj.name

        # Pack class name
        encoded_class = class_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_class)))
        stream.write(encoded_class)

        # Pack value name
        encoded_name = value_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_name)))
        stream.write(encoded_name)
    elif isinstance(obj, BaseParams):  # Check for BaseParams
        stream.write(TYPE_BASEPARAMS)
        # Store class name for reconstruction
        class_name = obj.__class__.__name__
        encoded_class = class_name.encode("utf-8")
        stream.write(struct.pack(">I", len(encoded_class)))
        stream.write(encoded_class)

        # Pack the _param_dict
        pack_obj(obj.__dict__, stream)
    elif isinstance(obj, bytes):
        stream.write(TYPE_BYTES)
        stream.write(struct.pack(">I", len(obj)))  # 4-byte length prefix
        stream.write(obj)
    elif isinstance(obj, set):
        stream.write(TYPE_SET)
        stream.write(struct.pack(">I", len(obj)))  # number of elements
        for item in obj:
            pack_obj(item, stream)
    else:
        raise TypeError(f"Unsupported type: {type(obj)}")


@dataclass
class EnumData:
    class_name: str
    value_name: str


@dataclass
class BaseParamsData:
    class_name: str
    param_dict: dict


def unpack_obj(stream: io.IOBase) -> Any:
    """Recursively unpack an object from the stream."""
    type_marker = stream.read(1)
    if not type_marker:
        raise EOFError("Unexpected end of stream")

    if type_marker == TYPE_NONE:
        return None
    elif type_marker == TYPE_BOOL_FALSE:
        return False
    elif type_marker == TYPE_BOOL_TRUE:
        return True
    elif type_marker == TYPE_INT:
        data = stream.read(8)
        return struct.unpack(">q", data)[0]
    elif type_marker == TYPE_FLOAT:
        data = stream.read(8)
        return struct.unpack(">d", data)[0]
    elif type_marker == TYPE_STR:
        (length,) = struct.unpack(">I", stream.read(4))
        data = stream.read(length)
        return data.decode("utf-8")
    elif type_marker == TYPE_LIST:
        (length,) = struct.unpack(">I", stream.read(4))
        lst = []
        for _ in range(length):
            lst.append(unpack_obj(stream))
        return lst
    elif type_marker == TYPE_TUPLE:
        (length,) = struct.unpack(">I", stream.read(4))
        lst = []
        for _ in range(length):
            lst.append(unpack_obj(stream))
        return tuple(lst)
    elif type_marker == TYPE_DICT:
        (length,) = struct.unpack(">I", stream.read(4))
        d = {}
        for _ in range(length):
            key = unpack_obj(stream)
            value = unpack_obj(stream)
            d[key] = value
        return d
    elif type_marker == TYPE_NDARRAY:
        # Read dtype string length (1 byte) and dtype string
        dtype_length = struct.unpack(">B", stream.read(1))[0]
        dtype_str = stream.read(dtype_length).decode("utf-8")
        # Read shape: number of dimensions and each dimension (4 bytes each)
        ndim = struct.unpack(">B", stream.read(1))[0]
        shape = struct.unpack(f">{ndim}I", stream.read(4 * ndim))
        # Calculate data length from shape and dtype
        dtype = np.dtype(dtype_str)
        data_length = dtype.itemsize * np.prod(shape)

        data = stream.read(data_length)
        arr = np.frombuffer(data, dtype=dtype).reshape(shape)

        return arr

    elif type_marker == TYPE_PATH:
        (length,) = struct.unpack(">I", stream.read(4))
        data = stream.read(length)
        return Path(data.decode("utf-8"))
    elif type_marker == TYPE_DATETIME:
        data = stream.read(8)
        timestamp = struct.unpack(">d", data)[0]
        return datetime.datetime.fromtimestamp(timestamp)
    elif type_marker == TYPE_ENUM:
        # Read class name
        class_len = struct.unpack(">I", stream.read(4))[0]
        class_name = stream.read(class_len).decode("utf-8")

        # Read value name
        value_len = struct.unpack(">I", stream.read(4))[0]
        value_name = stream.read(value_len).decode("utf-8")

        return EnumData(class_name=class_name, value_name=value_name)
    elif type_marker == TYPE_BASEPARAMS:
        # Read class name
        class_len = struct.unpack(">I", stream.read(4))[0]
        class_name = stream.read(class_len).decode("utf-8")

        # Read param dict
        param_dict = unpack_obj(stream)

        return BaseParamsData(class_name=class_name, param_dict=param_dict)
    elif type_marker == TYPE_BYTES:
        length = struct.unpack(">I", stream.read(4))[0]
        return stream.read(length)
    elif type_marker == TYPE_SET:
        (length,) = struct.unpack(">I", stream.read(4))
        result_set = set()
        for _ in range(length):
            result_set.add(unpack_obj(stream))
        return result_set
    else:
        raise ValueError(f"Unknown type marker: {type_marker}")
