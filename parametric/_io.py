from pathlib import Path
from typing import Any

import yaml


def load_from_yaml_path(yaml_path: Path | str) -> dict[str, Any]:
    yaml_path = process_filepath(yaml_path)

    with open(yaml_path, "r") as file:
        yaml_data = yaml.safe_load(file)
    # None returns if file is empty
    if yaml_data is None:
        yaml_data = {}
    return yaml_data


def process_filepath(filepath: Path | str) -> Path:
    filepath = Path(filepath)
    if not filepath.is_file():
        raise FileNotFoundError(f"No such file: '{filepath}'")
    return filepath
