import copy
from pathlib import Path
from types import UnionType
from typing import Any, Union

from nicegui import app, events, ui
from typing_extensions import get_args

# avoid circ dep. we only need this for annotation highlighting
if __name__ == "__main__":
    from parametric._base_params import BaseParams


def run_gui(params: "BaseParams"):
    # from parametric._base_params import BaseParams

    override_dict = {}

    copy_params = copy.deepcopy(params)
    for field_name, field_info in params.model_fields.items():
        _generate_ui_element(field_name, field_info.annotation, copy_params, override_dict)

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


def _generate_ui_element(field_name: str, typehint: Any, params: "BaseParams", override_dict: dict):
    print(typehint)
    if typehint in (int, float, str):  # bytes
        _basic_input(field_name, params, override_dict)
    elif typehint is bool:
        _bool_input(field_name, params, override_dict)
    elif typehint is type(None):
        ui.label("'None' is selected")
    # elif isinstance(type_node, TupleNode):
    #     pass
    # elif isinstance(type_node, BaseParamsNode):
    #     with ui.card():
    #         pass
    # elif isinstance(type_node, PathNode):
    #     pass
    elif type(typehint) in {Union, UnionType}:
        val = getattr(params, field_name)
        with ui.card():
            tabs_list = []
            with ui.tabs().classes("w-full") as ui_tabs:
                chosen_ind = -1
                for i, inner_arg in enumerate(get_args(typehint)):
                    tab_name = str(inner_arg)
                    ui.tab(tab_name)
                    tabs_list.append(tab_name)
                    if inner_arg not in (int, float, bool, str, bytes, Path, type(None)):
                        continue

                    if isinstance(val, inner_arg):
                        chosen_ind = i
                assert chosen_ind != -1

            with ui.tab_panels(ui_tabs, value=tabs_list[chosen_ind]).classes("w-full"):
                for t in tabs_list:
                    with ui.tab_panel(t):
                        ui.label("test")

                        # _generate_ui_element(None, inner_arg, params)
    ui.separator()


def _bool_input(field_name: str | None, params: "BaseParams", override_dict: dict):
    if field_name is not None:
        ui.label(field_name)

    value = getattr(params, field_name)
    opt = ["True", "False"]
    ui.toggle(
        opt,
        value=opt[int(value)],
        on_change=lambda e, name=field_name, override_dict=override_dict: _on_change(e, name, override_dict),
    )


def _basic_input(name: str | None, params: "BaseParams", override_dict):
    if name is not None:
        ui.label(name)
    value = getattr(params, name)
    ui.input(
        placeholder=value,
        value=value,
        on_change=lambda e, name=name, override_dict=override_dict: _on_change(e, name, override_dict),
        validation={"Not valid input": lambda value: _is_valid_type(value, name, params)},
    )


def _on_change(e: events.ValueChangeEventArguments, name: str, override_dict: dict):
    value = e.value
    if len(value) == 0 and name in override_dict:
        del override_dict[name]
    else:
        override_dict[name] = value


def _is_valid_type(value: Any, name: str, params: "BaseParams") -> bool:
    if len(value) == 0:
        return True

    try:
        setattr(params, name, value)
    except Exception:
        return False
    return True


if __name__ == "__main__":
    from tests.conftest import MyParams

    params = MyParams()
    params.override_gui()
    print("hi")
    print("hi2")
    print("hi3")
    print("hi4")
