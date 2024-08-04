from typing import Union

from parametric._base_params import wrangle_type


def test_union_type_prefer_no_coercion():
    # Test with str|int and value 1, should return (1, False) because no coercion needed
    assert wrangle_type("test_field", 1, Union[str, int]) == (1, False)

    # Test with str|int and value "1", should return ("1", False) because no coercion needed
    assert wrangle_type("test_field", "1", Union[str, int]) == ("1", False)

    # Test with str|float|int and value 1.5, should return (1.5, False) because no coercion needed
    assert wrangle_type("test_field", 1.5, Union[str, float, int]) == (1.5, False)

    # Test with str|float|int and value 1, should return (1, False) because no coercion needed
    assert wrangle_type("test_field", 1, Union[str, float, int]) == (1, False)

    # Test with float|str|int and value 1, should return (1, False) because no coercion needed
    assert wrangle_type("test_field", 1, Union[float, str, int]) == (1, False)

    # Test with tuple|str|int and value (1, 2), should return ((1, 2), False) because no coercion needed
    assert wrangle_type("test_field", (1, 2), Union[str, tuple[int, int], int]) == ((1, 2), False)

    # Test with str|None and value None, should return (None, False) because no coercion needed
    assert wrangle_type("test_field", None, Union[str, None]) == (None, False)


def test_union_type_fallback_to_coercion():
    # Test with str|int and value "1", should return ("1", False) because no coercion needed
    assert wrangle_type("test_field", "1", Union[int, str]) == ("1", False)

    # Test with float|int and value "1", should return (1, True) because coercion was needed
    assert wrangle_type("test_field", "1", Union[float, int]) == (1, True)

    # Test with float|str|int and value "1.5", should return (1.5, True) because coercion was needed
    assert wrangle_type("test_field", "1.5", Union[int, float]) == (1.5, True)
