from complex_base_params import MyParams

from parametric._field_eq_check import is_equal_field
from tests.tmp_file_context import CreateTmpFile


def test_save_and_load_from_msgpack(params: MyParams):
    with CreateTmpFile(suffix=".msgpack") as tmp_msgpack:
        params.save_msgpack(tmp_msgpack.filepath)
        loaded_params = MyParams.load_msgpack(tmp_msgpack.filepath)

    # First try the normal equality check
    if params != loaded_params:
        # If equality fails, check field by field to identify the problematic one(s)
        _check_fields_recursively(params, loaded_params)


def _check_fields_recursively(obj1, obj2, parent_path=""):
    """Recursively compare fields between two BaseParams objects."""
    from parametric import BaseParams

    for field_name in obj1._get_annotations():
        current_path = f"{parent_path}.{field_name}" if parent_path else field_name
        original_value = getattr(obj1, field_name)
        loaded_value = getattr(obj2, field_name)

        if isinstance(original_value, BaseParams):
            # Recursively check nested BaseParams
            if not isinstance(loaded_value, BaseParams):
                raise AssertionError(
                    f"Field '{current_path}' type mismatch:\n"
                    f"  Original: {type(original_value)}\n"
                    f"  Loaded: {type(loaded_value)}"
                )
            _check_fields_recursively(original_value, loaded_value, current_path)
        elif not is_equal_field(original_value, loaded_value):
            raise AssertionError(
                f"Field '{current_path}' differs:\n"
                f"  Original: {original_value} (type: {type(original_value)})\n"
                f"  Loaded: {loaded_value} (type: {type(loaded_value)})"
            )
