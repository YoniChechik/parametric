from tests.conftest import MyParams


def test_change_on_init(params: MyParams):
    params = MyParams(s01="test")
    assert params.s01 == "test"
    assert params.model_dump_non_defaults() == {"s01": "test"}
