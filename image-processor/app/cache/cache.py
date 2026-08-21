import json
from pathlib import Path


CACHE_FILE = Path(
    "/app/config/cache.json"
)

CACHE_VERSION = 3


class CacheManager:

    def __init__(self):
        self.data = {
            "version": CACHE_VERSION,
            "items": {}
        }

        self.load()

    # ============================================================
    # Load
    # ============================================================

    def load(self):

        if not CACHE_FILE.exists():
            return

        try:

            loaded = json.loads(
                CACHE_FILE.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError
        ):
            print(
                "[WARN] Failed loading cache.json",
                flush=True
            )

            return

        if not isinstance(
            loaded,
            dict
        ):
            print(
                "[WARN] Invalid cache.json format",
                flush=True
            )

            return

        if loaded.get(
            "version"
        ) != CACHE_VERSION:

            print(
                "[WARN] Unsupported cache.json version",
                flush=True
            )

            return

        items = loaded.get(
            "items"
        )

        if not isinstance(
            items,
            dict
        ):
            print(
                "[WARN] Invalid cache.json items",
                flush=True
            )

            return

        self.data = {
            "version": CACHE_VERSION,
            "items": items
        }

    # ============================================================
    # Save
    # ============================================================

    def save(self):

        CACHE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_file = (
            CACHE_FILE.with_suffix(
                ".json.tmp"
            )
        )

        try:

            temporary_file.write_text(
                json.dumps(
                    self.data,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            temporary_file.replace(
                CACHE_FILE
            )

        except Exception:

            try:

                if temporary_file.exists():
                    temporary_file.unlink()

            except OSError:
                pass

            raise

    # ============================================================
    # Get
    # ============================================================

    def get(
        self,
        key
    ):

        return self.data[
            "items"
        ].get(
            key
        )

    # ============================================================
    # Set
    # ============================================================

    def set(
        self,
        key,
        value
    ):

        self.data[
            "items"
        ][key] = value

    # ============================================================
    # Remove
    # ============================================================

    def remove(
        self,
        key
    ):

        self.data[
            "items"
        ].pop(
            key,
            None
        )

    # ============================================================
    # Keys
    # ============================================================

    def keys(self):

        return set(
            self.data[
                "items"
            ].keys()
        )

    # ============================================================
    # Empty
    # ============================================================

    def is_empty(self):

        return not self.data[
            "items"
        ]

    # ============================================================
    # Clear
    # ============================================================

    def clear(self):

        self.data = {
            "version": CACHE_VERSION,
            "items": {}
        }