import msgpack

from parametric import BaseParams
from tests.conftest import MyParams
from tests.tmp_file_context import CreateTmpFile


def test_msgpack_override(params: MyParams):
    with CreateTmpFile(suffix=".msgpack") as tmp_msgpack:
        params.save_msgpack(tmp_msgpack.filepath)

        # Reload params and ensure equality
        params2 = MyParams()
        params2.override_from_msgpack_path(tmp_msgpack.filepath)

    assert params == params2


def test_load_from_msgpack():
    class Test(BaseParams):
        f01: float
        f02: float = 0
        f03: float = 0.1

    with CreateTmpFile(suffix=".msgpack") as tmp_msgpack:
        data = {"f01": 1, "f02": 2, "f03": 3}
        with open(tmp_msgpack.filepath, "wb") as f:
            f.write(msgpack.packb(data))

        t = Test.load_from_msgpack_path(tmp_msgpack.filepath)

    assert t.f01 == 1
    assert t.f02 == 2
    assert t.f03 == 3
