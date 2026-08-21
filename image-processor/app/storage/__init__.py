from app.storage.github import GitHubStorage
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


def create_storage(
    name,
    config
):
    storage_type = config.get(
        "type"
    )

    if storage_type == "local":
        return LocalStorage(
            config
        )

    if storage_type == "github":
        return GitHubStorage(
            config
        )

    if storage_type == "s3":
        return S3Storage(
            config,
            name=name
        )

    raise ValueError(
        f"Unsupported storage type: {storage_type}"
    )