from parametric import BaseParams


def test_equality_check():
    class Nested(BaseParams):
        param: int = 5

    class Test(BaseParams):
        param2: int = 5
        nested: Nested = Nested(param=6)

    instance = Test()

    # ===== other is not BaseParams instance
    assert instance != 5

    # ===== copy of instance but with different value
    other = Test()
    assert instance == other

    other.override_from_dict({"param2": 10})
    assert instance != other

    # ======= different baseParams with same key name
    class Test2(BaseParams):
        param2: int = 10

    other = Test2()
    assert instance != other

    # ======= different baseParams with different key name
    class Test3(BaseParams):
        param3: int = 5

    other = Test3()
    assert instance != other
