from pathlib import Path


def process_filepath(filepath: Path | str) -> Path:
    filepath = Path(filepath)
    if not filepath.is_file():
        raise FileNotFoundError(f"No such file: '{filepath}'")
    return filepath
