from tests.conftest import MyParams


def test_model_dump_serializable(params: MyParams):
    params_dict = params.model_dump_serializable()
    assert params_dict["p03"] == "/xx/path"


def test_model_dump_non_defaults(params: MyParams):
    params.override_from_dict({"f04": 0.001, "bp01": {"i01": 10000}})
    assert params.f04 == 0.001
    assert params.bp01.i01 == 10000

    assert params.model_dump_non_defaults() == {"f04": 0.001, "bp01": {"i01": 10000}}
