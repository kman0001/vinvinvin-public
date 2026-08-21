from abc import ABC, abstractmethod
from pathlib import Path


class Storage(ABC):

    def __init__(
        self,
        config
    ):
        self.config = config

    @abstractmethod
    def upload(
        self,
        source: Path,
        destination: str
    ):
        """
        파일을 storage에 업로드한다.

        반환값:

        {
            "path": str,
            "url": str | None
        }
        """
        pass

    @abstractmethod
    def delete(
        self,
        destination: str
    ):
        pass

    @abstractmethod
    def exists(
        self,
        destination: str
    ):
        pass

    def download(
        self,
        source,
        destination
    ):
        raise NotImplementedError

    def flush(self):
        pass