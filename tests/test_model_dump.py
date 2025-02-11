from tests.conftest import MyParams


def test_model_dump_non_defaults(params: MyParams):
    params.f04 = 0.001
    params.bp01.i01 = 10000

    assert params.model_dump_non_defaults() == {"f04": 0.001, "bp01": {"i01": 10000}}
