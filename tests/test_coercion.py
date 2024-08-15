from typing import Union

from parametric._base_params import wrangle_type
from parametric._wrangle_type import WrangleTypeReturn


def test_union_type_prefer_no_coercion():
    # Test with str|int and value 1, should return (1, False) because no coercion needed
    assert _compare_wrangle_type_returns(wrangle_type("test_field", 1, Union[str, int]), WrangleTypeReturn(1, False))

    # Test with str|int and value "1", should return ("1", False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", "1", Union[str, int]), WrangleTypeReturn("1", False)
    )

    # Test with str|float|int and value 1.5, should return (1.5, False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", 1.5, Union[str, float, int]), WrangleTypeReturn(1.5, False)
    )

    # Test with str|float|int and value 1, should return (1, False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", 1, Union[str, float, int]), WrangleTypeReturn(1, False)
    )

    # Test with float|str|int and value 1, should return (1, False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", 1, Union[float, str, int]), WrangleTypeReturn(1, False)
    )

    # Test with tuple|str|int and value (1, 2), should return ((1, 2), False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", (1, 2), Union[str, tuple[int, int], int]), WrangleTypeReturn((1, 2), False)
    )

    # Test with str|None and value None, should return (None, False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", None, Union[str, None]), WrangleTypeReturn(None, False)
    )


def test_union_type_fallback_to_coercion():
    # Test with str|int and value "1", should return ("1", False) because no coercion needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", "1", Union[int, str]), WrangleTypeReturn("1", False)
    )

    # Test with float|int and value "1", should return (1, True) because coercion was needed
    assert _compare_wrangle_type_returns(wrangle_type("test_field", "1", Union[float, int]), WrangleTypeReturn(1, True))

    # Test with float|str|int and value "1.5", should return (1.5, True) because coercion was needed
    assert _compare_wrangle_type_returns(
        wrangle_type("test_field", "1.5", Union[int, float]), WrangleTypeReturn(1.5, True)
    )


def _compare_wrangle_type_returns(a: WrangleTypeReturn, b: WrangleTypeReturn) -> bool:
    if not isinstance(a, WrangleTypeReturn) or not isinstance(b, WrangleTypeReturn):
        return False
    return (a.converted_value == b.converted_value) and (a.is_coerced == b.is_coerced)
