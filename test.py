import json
import pathlib
from typing import Type, TypeVar

import msgspec
import msgspec.json
import msgspec.msgpack
import numpy as np
import toml
import yaml

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
      - np.ndarray: Encoded as an extension containing (dtype_str, shape, raw_bytes)
      - pathlib.Path: Encoded as a POSIX string.
    """
    if isinstance(obj, np.ndarray):
        dtype_str = obj.dtype.str
        payload = msgspec.msgpack.encode((dtype_str, obj.shape, obj.tobytes()))
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
    MessagePack extension hook to reconstitute a numpy array.
    """
    if code == NDARRAY_EXT_CODE:
        dtype_str, shape, raw_bytes = msgspec.msgpack.decode(data)
        arr = np.frombuffer(raw_bytes, dtype=np.dtype(dtype_str))
        return arr.reshape(shape)
    raise NotImplementedError(f"Extension type code {code} is not supported in {msgpack_dec_ext_hook.__name__}")


# ------------------------------------------------------------------------------
# Custom hooks for serialization
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
    if expected_type is np.ndarray and isinstance(obj, list):
        return np.array(obj)
    if expected_type is pathlib.Path and isinstance(obj, str):
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
    def from_msgpack(cls: Type[T], data: bytes) -> T:
        """
        Deserialize MessagePack bytes into an instance of the calling class.
        """
        decoder = msgspec.msgpack.Decoder(cls, ext_hook=msgpack_dec_ext_hook, dec_hook=msgpack_dec_hook)
        return decoder.decode(data)

    # -- JSON serialization --

    def to_json(self) -> str:
        """
        Serialize the instance to a JSON string using custom hooks.
        """
        json_bytes = msgspec.json.encode(self, enc_hook=serialization_enc_hook)
        return json_bytes.decode("utf-8")

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Deserialize a JSON string into an instance of the calling class.
        """
        return msgspec.json.decode(json_str.encode("utf-8"), type=cls, dec_hook=serialization_dec_hook)

    # -- Dict conversion (via JSON round-trip) --

    def to_dict(self) -> dict:
        """
        Convert the instance to a dict (using a JSON round-trip).
        """
        json_bytes = msgspec.json.encode(self, enc_hook=serialization_enc_hook)
        return msgspec.json.decode(json_bytes)

    @classmethod
    def from_dict(cls: Type[T], d: dict) -> T:
        """
        Instantiate an instance from a dict (via JSON round-trip).
        """
        json_str = json.dumps(d)
        return cls.from_json(json_str)

    # -- YAML serialization (using dict conversion) --

    def to_yaml(self) -> str:
        """
        Serialize the instance to a YAML string.
        """
        d = self.to_dict()
        return yaml.safe_dump(d)

    @classmethod
    def from_yaml(cls: Type[T], yaml_str: str) -> T:
        """
        Deserialize a YAML string into an instance of the calling class.
        """
        d = yaml.safe_load(yaml_str)
        return cls.from_dict(d)

    # -- TOML serialization (using dict conversion) --

    def to_toml(self) -> str:
        """
        Serialize the instance to a TOML string.
        """
        d = self.to_dict()
        return toml.dumps(d)

    @classmethod
    def from_toml(cls: Type[T], toml_str: str) -> T:
        """
        Deserialize a TOML string into an instance of the calling class.
        """
        d = toml.loads(toml_str)
        return cls.from_dict(d)


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
class SimpleModel(MsgpackModel):
    name: str
    value: int
    file: pathlib.Path


# ------------------------------------------------------------------------------
# Main tests for all serialization methods
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running tests for extended MsgpackModel with pathlib.Path and JSON np.ndarray as list...")

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

    # Dict round-trip
    d = model1.to_dict()
    model1_dict = MyModel.from_dict(d)
    assert np.array_equal(model1.array, model1_dict.array)
    for orig, dec in zip(model1.arrays, model1_dict.arrays):
        assert np.array_equal(orig, dec)
    assert model1.path.as_posix() == model1_dict.path.as_posix()
    print("Test 1c passed: Dict conversion for MyModel with pathlib.Path.")

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

    # --- Test 4: SimpleModel with native types and a pathlib.Path ---
    simple = SimpleModel(name="TestModel", value=123, file=pathlib.Path("some/file"))
    simple_toml = SimpleModel.from_toml(simple.to_toml())
    assert simple.name == simple_toml.name and simple.value == simple_toml.value
    assert simple.file.as_posix() == simple_toml.file.as_posix()
    print("Test 4 passed: SimpleModel encoded/decoded correctly via TOML with pathlib.Path.")

    print("All tests passed successfully!")
