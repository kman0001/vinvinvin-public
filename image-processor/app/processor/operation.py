from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class UploadOperation:
    key: str
    source: Path
    destination: str


@dataclass(slots=True)
class DeleteOperation:
    key: str
    destination: str