from parametric._base_params import BaseParams
from tests.conftest import MyParams


def test_change_on_init(params: MyParams):
    params = MyParams(s01="test")
    assert params.s01 == "test"
    assert params.model_dump_non_defaults() == {"s01": "test"}


def test_change_on_init_no_default():
    class Test(BaseParams):
        s01: str

    t = Test(s01="test")
    assert t.s01 == "test"
    assert t.model_dump_non_defaults() == {"s01": "test"}
