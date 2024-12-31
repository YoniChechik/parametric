import os
from pathlib import Path
from tempfile import NamedTemporaryFile


class CreateTmpFile:
    def __init__(self, suffix: str | None = None, data: str = ""):
        self.suffix: str = suffix
        self.data: str = data

    def __enter__(self):
        with NamedTemporaryFile("w", delete=False, suffix=self.suffix) as tmp_file:
            self.filepath = Path(tmp_file.name)
            tmp_file.write(self.data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove(self.filepath)
