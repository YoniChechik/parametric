from parametric import BaseParams


def test_error_base_params_instance_not_int():
    class Test(BaseParams):
        param: int = 5

    instance = Test()

    # other is not BaseParams instance
    assert instance != 5

    # copy of instance but with different value
    other = Test()
    assert instance == other

    other.override_from_dict({"param": 10})
    assert instance != other

    # differnt BaseParams object
    class Test2(BaseParams):
        param2: int = 10

    other = Test2()
    assert instance != other
