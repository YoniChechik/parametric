import pathlib
import struct
import time
from typing import Type, TypeVar

import msgspec
import msgspec.json
import msgspec.msgpack
import numpy as np
from typing_extensions import Buffer

# Type variable for return type hints
T = TypeVar("T", bound="MsgpackModel")

# ------------------------------------------------------------------------------
# Custom hooks for MessagePack
# ------------------------------------------------------------------------------

# Choose an arbitrary extension type code (must be between 0 and 127)
NDARRAY_EXT_CODE = 42


def msgpack_enc_hook(obj: object) -> object:
    """
    MessagePack encoder hook that handles:
      - np.ndarray: Encodes as an extension with a binary header.
      - pathlib.Path: Encoded as a POSIX string.

    For np.ndarray, the header is structured as:
        [4-byte unsigned int: length of dtype string]
        [dtype string in ASCII]
        [4-byte unsigned int: number of dimensions]
        [for each dimension: 4-byte unsigned int]
    followed by the raw array bytes.
    """
    if isinstance(obj, np.ndarray):
        dtype_bytes = obj.dtype.str.encode("ascii")
        shape = obj.shape
        header = struct.pack("!I", len(dtype_bytes)) + dtype_bytes
        header += struct.pack("!I", len(shape)) + struct.pack(f"!{len(shape)}I", *shape)
        payload = header + obj.reshape(-1).tobytes()  # Flatten to avoid unnecessary reshaping
        return msgspec.msgpack.Ext(NDARRAY_EXT_CODE, payload)
    elif isinstance(obj, pathlib.Path):
        return obj.as_posix()
    raise NotImplementedError(f"Object of type {type(obj)} is not supported in {msgpack_enc_hook.__name__}")


def msgpack_dec_hook(expected_type: Type, obj: object) -> object:
    """
    Additional MessagePack decoder hook that handles:
    If a field is expected to be a pathlib.Path and the value is a string,
    convert it using pathlib.Path.
    """
    if expected_type is pathlib.Path:
        return pathlib.Path(obj)
    return obj


def msgpack_dec_ext_hook(code: int, data: memoryview) -> object:
    """
    Optimized MessagePack extension hook for deserializing a numpy array.
    """
    if code == NDARRAY_EXT_CODE:
        offset = 0
        # Read dtype length and dtype string
        dtype_len = struct.unpack_from("!I", data, offset)[0]
        offset += 4
        dtype_str = data[offset : offset + dtype_len].tobytes().decode("ascii")
        offset += dtype_len
        # Read the number of dimensions
        ndim = struct.unpack_from("!I", data, offset)[0]
        offset += 4
        shape = struct.unpack_from(f"!{ndim}I", data, offset)
        offset += ndim * 4
        # Compute expected byte size
        dt = np.dtype(dtype_str)
        expected_size = int(np.prod(shape)) * dt.itemsize
        # Extract only the required number of bytes
        raw_bytes = memoryview(data[offset : offset + expected_size])
        arr = np.frombuffer(raw_bytes, dtype=dt).reshape(shape)
        return arr
    raise NotImplementedError(f"Extension type code {code} is not supported in {msgpack_dec_ext_hook.__name__}")


# ------------------------------------------------------------------------------
# Custom hooks for serialization (JSON, etc.)
# ------------------------------------------------------------------------------


def serialization_enc_hook(obj: object) -> object:
    """
    JSON encoder hook that handles:
      - np.ndarray: Converts to a Python list.
      - pathlib.Path: Converts to a POSIX string.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pathlib.Path):
        return obj.as_posix()
    raise NotImplementedError(f"Object of type {type(obj)} is not supported in {serialization_enc_hook.__name__}")


def serialization_dec_hook(expected_type: Type, obj: object) -> object:
    """
    JSON decoder hook that handles:
      - np.ndarray: If a list is encountered and an np.ndarray is expected,
                    convert it with np.array().
      - pathlib.Path: If a string is encountered and pathlib.Path is expected,
                      convert it with pathlib.Path().
    """
    if expected_type is np.ndarray:
        return np.asarray(obj)
    if expected_type is pathlib.Path:
        return pathlib.Path(obj)
    return obj


# ------------------------------------------------------------------------------
# Base class for models with multiple serialization methods
# ------------------------------------------------------------------------------


class MsgpackModel(msgspec.Struct):
    """
    Abstract base class for models that support serialization/deserialization
    via MessagePack, JSON, dict, YAML, and TOML. It has built-in support for:
      - np.ndarray (using binary extension in MessagePack; list conversion in JSON)
      - pathlib.Path (encoded as POSIX strings)

    This class is meant to be subclassed only.
    """

    def __post_init__(self):
        # Prevent direct instantiation of the base class.
        if type(self) is MsgpackModel:
            raise TypeError("MsgpackModel is an abstract base class; please subclass it.")

    # -- MessagePack serialization --

    def to_msgpack(self) -> bytes:
        """
        Serialize the instance to MessagePack bytes.
        """
        encoder = msgspec.msgpack.Encoder(enc_hook=msgpack_enc_hook)
        return encoder.encode(self)

    @classmethod
    def from_msgpack(cls: Type[T], data: Buffer) -> T:
        """
        Deserialize MessagePack bytes into an instance of the calling class.
        """
        decoder = msgspec.msgpack.Decoder(cls, ext_hook=msgpack_dec_ext_hook, dec_hook=msgpack_dec_hook)
        return decoder.decode(data)

    def to_msgpack_path(self, path: pathlib.Path | str) -> None:
        """
        Serialize the instance to MessagePack bytes and save to a file.
        """
        # TODO use  this to write to file efficient       encoder = msgspec.msgpack.Encoder(enc_hook=msgpack_enc_hook); encoder.encode_into(self,buffer,offset)

        with open(path, "wb") as f:
            f.write(self.to_msgpack())

    @classmethod
    def from_msgpack_path(cls: Type[T], path: pathlib.Path | str) -> T:
        """
        Deserialize MessagePack bytes from a file into an instance of the calling class
        without unnecessary copies.
        """
        with open(path, "rb") as f:
            data = f.read()
        return cls.from_msgpack(data)

    # -- JSON serialization --

    def to_json(self) -> str:
        """
        Serialize the instance to a JSON string using custom hooks.
        """
        return msgspec.json.encode(self, enc_hook=serialization_enc_hook).decode("utf-8")

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Deserialize a JSON string into an instance of the calling class.
        """
        return msgspec.json.decode(json_str.encode("utf-8"), type=cls, dec_hook=serialization_dec_hook)

    def to_json_path(self, path: pathlib.Path | str) -> None:
        """
        Serialize the instance to a JSON string and save to a file.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_json_path(cls: Type[T], path: pathlib.Path | str) -> T:
        """
        Deserialize a JSON string from a file into an instance of the calling class.
        """
        with open(path, "r", encoding="utf-8") as f:
            json_str = f.read()
        return cls.from_json(json_str)

    # -- YAML serialization (using dict conversion) --

    def to_yaml(self) -> str:
        """
        Serialize the instance to a YAML string.
        """
        return msgspec.yaml.encode(self, enc_hook=serialization_enc_hook).decode("utf-8")

    @classmethod
    def from_yaml(cls: Type[T], yaml_str: str) -> T:
        """
        Deserialize a YAML string into an instance of the calling class.
        """

        return msgspec.yaml.decode(yaml_str.encode("utf-8"), type=cls, dec_hook=serialization_dec_hook)

    def to_yaml_path(self, path: pathlib.Path | str) -> None:
        """
        Serialize the instance to a YAML string and save to a file.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())

    @classmethod
    def from_yaml_path(cls: Type[T], path: pathlib.Path | str) -> T:
        """
        Deserialize a YAML string from a file into an instance of the calling class.
        """
        with open(path, "r", encoding="utf-8") as f:
            yaml_str = f.read()
        return cls.from_yaml(yaml_str)

    # -- TOML serialization (using dict conversion) --

    def to_toml(self) -> str:
        """
        Serialize the instance to a TOML string.
        """
        return msgspec.toml.encode(self, enc_hook=serialization_enc_hook).decode("utf-8")

    @classmethod
    def from_toml(cls: Type[T], toml_str: str) -> T:
        """
        Deserialize a TOML string into an instance of the calling class.
        """
        return msgspec.toml.decode(toml_str.encode("utf-8"), type=cls, dec_hook=serialization_dec_hook)

    def to_toml_path(self, path: pathlib.Path | str) -> None:
        """
        Serialize the instance to a TOML string and save to a file.
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_toml())

    @classmethod
    def from_toml_path(cls: Type[T], path: pathlib.Path | str) -> T:
        """
        Deserialize a TOML string from a file into an instance of the calling class.
        """
        with open(path, "r", encoding="utf-8") as f:
            toml_str = f.read()
        return cls.from_toml(toml_str)


# ------------------------------------------------------------------------------
# Derived Models and Tests
# ------------------------------------------------------------------------------


# Test 1: A simple model with np.ndarray fields and a pathlib.Path field.
class MyModel(MsgpackModel):
    array: np.ndarray  # single numpy array field
    arrays: list[np.ndarray]  # list of numpy arrays
    path: pathlib.Path  # a file/directory path


# Test 2: A model that nests another model as an inner class.
class Outer(MsgpackModel):
    class Inner(MsgpackModel):
        value: int
        arr: np.ndarray
        p: pathlib.Path

    inner: Inner


# Test 3: A model that contains a list of other models.
class Container(MsgpackModel):
    items: list[MyModel]


# Test 4: A model with only native types (including pathlib.Path).
class InheritedModel(Container):
    name: str
    value: int
    file: pathlib.Path = pathlib.Path("some/file")


# ------------------------------------------------------------------------------
# Main tests for all serialization methods
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running tests for optimized MsgpackModel with pathlib.Path and np.ndarray handling...")

    # --- Test 1: MyModel with numpy arrays and a pathlib.Path ---
    arr = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
    arr_list = [np.array([1.1, 2.2], dtype=np.float64), np.array([3.3, 4.4], dtype=np.float64)]
    my_path = pathlib.Path("some/directory/file.txt")
    model1 = MyModel(array=arr, arrays=arr_list, path=my_path)

    # MessagePack round-trip
    mp_bytes = model1.to_msgpack()
    model1_mp = MyModel.from_msgpack(mp_bytes)
    assert np.array_equal(model1.array, model1_mp.array)
    for orig, dec in zip(model1.arrays, model1_mp.arrays):
        assert np.array_equal(orig, dec)
    assert model1.path.as_posix() == model1_mp.path.as_posix()
    print("Test 1a passed: MessagePack encoding/decoding for MyModel with pathlib.Path.")

    # JSON round-trip
    json_str = model1.to_json()
    model1_json = MyModel.from_json(json_str)
    assert np.array_equal(model1.array, model1_json.array)
    for orig, dec in zip(model1.arrays, model1_json.arrays):
        assert np.array_equal(orig, dec)
    assert model1.path.as_posix() == model1_json.path.as_posix()
    print("Test 1b passed: JSON encoding/decoding for MyModel with pathlib.Path.")

    # YAML round-trip
    yaml_str = model1.to_yaml()
    model1_yaml = MyModel.from_yaml(yaml_str)
    assert np.array_equal(model1.array, model1_yaml.array)
    for orig, dec in zip(model1.arrays, model1_yaml.arrays):
        assert np.array_equal(orig, dec)
    assert model1.path.as_posix() == model1_yaml.path.as_posix()
    print("Test 1d passed: YAML encoding/decoding for MyModel with pathlib.Path.")

    # TOML round-trip
    toml_str = model1.to_toml()
    model1_toml = MyModel.from_toml(toml_str)
    assert np.array_equal(model1.array, model1_toml.array)
    for orig, dec in zip(model1.arrays, model1_toml.arrays):
        assert np.array_equal(orig, dec)
    assert model1.path.as_posix() == model1_toml.path.as_posix()
    print("Test 1e passed: TOML encoding/decoding for MyModel with pathlib.Path.")

    # --- Test 2: Outer with nested Inner class (including pathlib.Path) ---
    inner_instance = Outer.Inner(value=42, arr=np.array([10, 20, 30], dtype=np.int16), p=pathlib.Path("inner/path"))
    outer_instance = Outer(inner=inner_instance)
    outer_mp = Outer.from_msgpack(outer_instance.to_msgpack())
    assert outer_mp.inner.value == inner_instance.value
    assert np.array_equal(outer_instance.inner.arr, outer_mp.inner.arr)
    assert outer_instance.inner.p.as_posix() == outer_mp.inner.p.as_posix()
    print("Test 2 passed: Outer with nested Inner encoded/decoded correctly.")

    # --- Test 3: Container with a list of MyModel instances ---
    model_a = MyModel(
        array=np.array([1, 2, 3], dtype=np.int32),
        arrays=[np.array([1.0, 2.0], dtype=np.float32)],
        path=pathlib.Path("a/path"),
    )
    model_b = MyModel(
        array=np.array([4, 5, 6], dtype=np.int32),
        arrays=[np.array([3.0, 4.0], dtype=np.float32)],
        path=pathlib.Path("b/path"),
    )
    container = Container(items=[model_a, model_b])
    container_json = Container.from_json(container.to_json())
    for orig, dec in zip(container.items, container_json.items):
        assert np.array_equal(orig.array, dec.array)
        for a, b in zip(orig.arrays, dec.arrays):
            assert np.array_equal(a, b)
        assert orig.path.as_posix() == dec.path.as_posix()
    print("Test 3 passed: Container with a list of MyModel instances round-trips correctly.")

    # --- Test 4: InheritedModel with native types (including pathlib.Path) ---
    simple = InheritedModel(items=[model_a], name="TestModel", value=123)
    simple_toml = InheritedModel.from_toml(simple.to_toml())
    assert simple.name == simple_toml.name and simple.value == simple_toml.value
    assert simple.file.as_posix() == simple_toml.file.as_posix()
    print("Test 4 passed: InheritedModel encoded/decoded correctly via TOML with pathlib.Path.")

    print("All tests passed successfully!")

    # Create a random 1000x1000 numpy array of floats
    random_array = np.random.rand(10000, 10000)

    # Time saving and loading using numpy's save and load
    np_save_path = "random_array.npy"
    start_time = time.time()
    np.save(np_save_path, random_array)
    np_save_duration = time.time() - start_time

    start_time = time.time()
    loaded_array_np = np.load(np_save_path)
    np_load_duration = time.time() - start_time

    assert np.array_equal(random_array, loaded_array_np)
    print(f"NumPy save duration: {np_save_duration:.6f} seconds")
    print(f"NumPy load duration: {np_load_duration:.6f} seconds")

    # Define a model with a single field for the numpy array
    class ArrayModel(MsgpackModel):
        array: np.ndarray

    model_instance = ArrayModel(array=random_array)

    # Time saving and loading using the custom model
    start_time = time.time()
    model_bytes = model_instance.to_msgpack_path("random_array.msgpack")
    model_save_duration = time.time() - start_time

    start_time = time.time()
    loaded_model_instance = ArrayModel.from_msgpack_path("random_array.msgpack")
    model_load_duration = time.time() - start_time

    assert np.array_equal(random_array, loaded_model_instance.array)
    print(f"Model save duration: {model_save_duration:.6f} seconds")
    print(f"Model load duration: {model_load_duration:.6f} seconds")
