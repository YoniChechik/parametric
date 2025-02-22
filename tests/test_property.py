from parametric import BaseParams


def test_property_getter():
    class Test(BaseParams):
        x: int = 10
        y: int = 20

        @property
        def sum_xy(self) -> int:
            return self.x + self.y

    params = Test()
    assert params.sum_xy == 30

    # Change x and verify property updates
    params.x = 15
    assert params.sum_xy == 35


def test_property_cannot_be_set():
    class Test(BaseParams):
        x: int = 10
        y: int = 20

        @property
        def sum_xy(self) -> int:
            return self.x + self.y

    params = Test()
    # Attempt to set property should raise AttributeError
    try:
        params.sum_xy = 100
        assert False, "Should have raised AttributeError"
    except AttributeError as e:
        assert "`sum_xy` is not a valid field in Test" in str(e)
