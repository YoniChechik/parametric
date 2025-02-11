import msgpack

from parametric import BaseParams
from tests.conftest import MyParams
from tests.tmp_file_context import CreateTmpFile


# TODO doesnt fully test msgpack
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


# TODO mixup t01 tuple and list (returned from msgpack)
def test_error_change_directly(params: MyParams):
    with CreateTmpFile(suffix=".msgpack") as tmp_msgpack:
        params.save_msgpack(tmp_msgpack.filepath)
        loaded_params = MyParams.load_from_msgpack_path(tmp_msgpack.filepath)

    assert params == loaded_params
