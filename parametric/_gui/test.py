#!/usr/bin/env python3
from nicegui import ui

from local_file_picker import local_file_picker


async def pick_file() -> None:
    result = await local_file_picker("~", is_multiple=True)
    ui.notify(f"You chose {result}")


@ui.page("/")
def index():
    ui.button("Choose file", on_click=pick_file, icon="folder")


ui.run()
