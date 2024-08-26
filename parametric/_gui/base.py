from typing import Any

from nicegui import app, events, ui

from parametric._type_node import (
    BaseParamsNode,
    BoolNode,
    BytesNode,
    ComplexNode,
    FloatNode,
    IntNode,
    NoneTypeNode,
    PathNode,
    StrNode,
    TupleNode,
    TypeNode,
    UnionNode,
)


def run_gui(
    name_to_type_node: dict[str, TypeNode],
    name_to_value: dict[str, Any],
):
    override_dict = {}

    for name, type_node in name_to_type_node.items():
        init_value = name_to_value[name]
        _generate_ui_element(override_dict, name, type_node, init_value)

    # ==== when hitting save button
    def apply_changes():
        ui.context.client.run_javascript("window.close();")
        app.shutdown()

    ui.button("Apply Changes", on_click=apply_changes)

    # ==== when tab is closed
    def on_disconnect():
        app.shutdown()

    app.on_disconnect(on_disconnect)

    # ==== run and blocks until shutdown because `reload=False`
    ui.run(port=1234, reload=False)

    return override_dict


def _generate_ui_element(override_dict, name: str | None, type_node, init_value: Any):
    if isinstance(type_node, (IntNode, FloatNode, BytesNode, StrNode, ComplexNode)):
        _basic_input(override_dict, type_node, init_value, name)
    elif isinstance(type_node, BoolNode):
        _bool_input(override_dict, init_value, name)
    elif isinstance(type_node, NoneTypeNode):
        ui.label("'None' is selected")
    elif isinstance(type_node, TupleNode):
        pass
    elif isinstance(type_node, BaseParamsNode):
        with ui.card():
            pass
    elif isinstance(type_node, PathNode):
        pass
    elif isinstance(type_node, UnionNode):
        with ui.card():
            tabs_list = []
            with ui.tabs().classes("w-full") as ui_tabs:
                for inner_arg in type_node.inner_args:
                    tabs_list.append(ui.tab(inner_arg.type_base_name))

            with ui.tab_panels(ui_tabs, value=tabs_list[type_node.chosen_ind]).classes("w-full"):
                for i, (inner_arg, tab) in enumerate(zip(type_node.inner_args, tabs_list)):
                    init_value = None

                    with ui.tab_panel(tab):
                        _generate_ui_element(override_dict, None, inner_arg, init_value)
    ui.separator()


def _bool_input(override_dict, init_value: bool | None, name: str | None = None):
    if name is not None:
        ui.label(name)

    value = str(init_value) if init_value is not None else None
    ui.toggle(
        ["True", "False"],
        value=value,
        on_change=lambda e, name=name, override_dict=override_dict: _on_change(e, name, override_dict),
    )


def _basic_input(override_dict: dict[str, Any], type_node: TypeNode, init_value: Any = None, name: str | None = None):
    if name is not None:
        ui.label(name)
    value = str(init_value) if init_value is not None else None
    ui.input(
        placeholder=value,
        value=value,
        on_change=lambda e, name=name, override_dict=override_dict: _on_change(e, name, override_dict),
        validation={
            f"Not valid input for {type_node.type_base_name}": lambda value, type_node=type_node: _is_valid_type(
                value, type_node
            )
        },
    )


def _on_change(e: events.ValueChangeEventArguments, name: str, override_dict: dict[str, Any]):
    value = e.value
    if len(value) == 0 and name in override_dict:
        del override_dict[name]
    else:
        override_dict[name] = value


def _is_valid_type(value, type_node: TypeNode) -> bool:
    if len(value) == 0:
        return True

    try:
        type_node.cast_python_relaxed(value)
    except Exception:
        return False
    return True


if __name__ == "__main__":
    from pathlib import Path
    from typing import Literal

    from parametric import BaseParams

    class MyValidationParams(BaseParams):
        validation_batch_size: int = 8
        validation_save_dir: Path = "/my_dir"

    class MyParams(BaseParams):
        num_classes_without_bg: int = 5
        scheduler_name: str | None = None
        image_shape: tuple[int, int] = (640, 480)
        dataset_name: Literal["a", "b", "c"] = "a"
        nn_encoder_name: str = "efficientnet-b0"
        save_dir_path: Path | None = "/my/path"
        complex_number: complex = 1000 + 1j
        some_bytes: bytes = b"abc123"
        init_lr: float = 1e-4
        is_dropout: bool = False
        data_dirs: tuple[Path, ...]
        validation: MyValidationParams = MyValidationParams()

    params = MyParams()
    params.override_gui()
    print("hi")
    print("hi2")
    print("hi3")
    print("hi4")
