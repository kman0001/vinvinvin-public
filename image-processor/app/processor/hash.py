import hashlib


def calculate_hash(
    path
):
    sha = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                8192
            )

            if not chunk:
                break

            sha.update(
                chunk
            )

    return sha.hexdigest()


def calculate_menu_hash(
    category,
    name
):
    value = (
        f"{category.strip()}\n"
        f"{name.strip()}"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        value
    ).hexdigest()