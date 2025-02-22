from tests.conftest import MyParams
from tests.tmp_file_context import CreateTmpFile


def test_save_and_load_from_msgpack():
    params = MyParams()
    with CreateTmpFile(suffix=".msgpack") as tmp_msgpack:
        params.save_msgpack(tmp_msgpack.filepath)
        loaded_params = MyParams.load_msgpack(tmp_msgpack.filepath)

    assert params == loaded_params
