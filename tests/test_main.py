from parametric import parametrize

def test_parametrize():
    assert parametrize("a", "b") == "Parameters: a, b"
