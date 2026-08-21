import json
import os
from pathlib import Path


CONFIG_DIR = Path("/app/config")
CONFIG_FILE = CONFIG_DIR / "config.json"


SUPPORTED_STORAGE_TYPES = {
    "github",
    "local",
    "r2",
    "s3",
}


OUTPUT_MODES = {
    "github": {"filename", "url"},
    "local": {"filename"},
    "r2": {"url"},
    "s3": {"url"},
}


EXPECTED_TYPES = {
    "github": "github",
    "local": "local",
    "r2": "s3",
    "s3": "s3",
}


DEFAULT_CONFIG = {
    "source": {
        "base_url": "https://your-website.com",
        "constants_path": "/js/config/constants.js",
        "timeout_seconds": 30
    },

    "category_map": {
        "글라스 와인": "Glass",
        "쿼터 보틀": "Quarter",
        "레드": "Red",
        "화이트": "White",
        "스파클링": "Sparkling",
        "맥주": "Beer",
        "위스키": "Whiskey",
        "꼬냑": "Cognac",
        "안주": "Snack"
    },

    "scheduler": {
        "enabled": True,
        "cron": "0 5,17 * * *"
    },

    "storage": {
        "github": {
            "enabled": False,
            "type": "github",
            "repository": "your-username/your-repo",
            "branch": "main",
            "path": "website/images",
            "output_mode": "filename",
            "base_url": "https://your-website.com/images",
            "token": "your-github-token"
        },

        "local": {
            "enabled": False,
            "type": "local",
            "path": "/app/images",
            "output_mode": "filename"
        },

        "r2": {
            "enabled": False,
            "type": "s3",
            "endpoint": "your-r2-endpoint",
            "bucket": "your-r2-bucket",
            "path": "your-r2-path",
            "output_mode": "url",
            "base_url": "https://pub-xxxxxxxxxxxxxxxx.r2.dev",
            "access_key": "your-r2-access-key",
            "secret_key": "your-r2-secret-key"
        },

        "s3": {
            "enabled": False,
            "type": "s3",
            "region": "your-s3-region",
            "bucket": "your-s3-bucket",
            "path": "your-s3-path",
            "output_mode": "url",
            "base_url": "https://your-s3-bucket.s3.amazonaws.com",
            "access_key": "your-s3-access-key",
            "secret_key": "your-s3-secret-key"
        }
    },

    "primary_storage": "local",

    "sheet_update": {
        "enabled": False,
        "url": "",
        "google_apps_secret": "your-google-apps-secret",
        "image_column": "사진",
        "timeout_seconds": 180
    }
}


def resolve_secret(value):
    if not isinstance(value, str):
        return ""

    value = value.strip()

    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(
            value[2:-1],
            ""
        )

    if value.startswith("env:"):
        return os.environ.get(
            value[4:],
            ""
        )

    return value


def create_default_config():
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with CONFIG_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            DEFAULT_CONFIG,
            f,
            indent=2,
            ensure_ascii=False
        )


def validate_config(config):
    """
    Validate the loaded configuration.

    Returns:
        bool: True if the configuration is valid.
    """

    if not isinstance(config, dict):
        print(
            "[ERROR] config.json must contain a JSON object.",
            flush=True
        )

        return False

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------

    source = config.get("source")

    if not isinstance(source, dict):
        print(
            "[ERROR] 'source' configuration is missing or invalid.",
            flush=True
        )

        return False

    timeout = source.get("timeout_seconds")

    if not isinstance(timeout, (int, float)) or timeout <= 0:
        print(
            "[ERROR] 'source.timeout_seconds' must be greater than 0.",
            flush=True
        )

        return False

    # ------------------------------------------------------------------
    # Category map
    # ------------------------------------------------------------------

    category_map = config.get(
        "category_map"
    )

    if not isinstance(category_map, dict):
        print(
            "[ERROR] 'category_map' configuration is missing or invalid.",
            flush=True
        )

        return False

    for category, prefix in category_map.items():

        if (
            not isinstance(category, str)
            or not category.strip()
        ):
            print(
                "[ERROR] 'category_map' contains an invalid category.",
                flush=True
            )

            return False

        if (
            not isinstance(prefix, str)
            or not prefix.strip()
        ):
            print(
                "[ERROR] 'category_map' contains an invalid prefix "
                f"for category: {category!r}.",
                flush=True
            )

            return False

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    scheduler = config.get("scheduler")

    if not isinstance(scheduler, dict):
        print(
            "[ERROR] 'scheduler' configuration is missing or invalid.",
            flush=True
        )

        return False

    if not isinstance(scheduler.get("enabled"), bool):
        print(
            "[ERROR] 'scheduler.enabled' must be true or false.",
            flush=True
        )

        return False

    cron = scheduler.get("cron")

    if not isinstance(cron, str) or not cron.strip():
        print(
            "[ERROR] 'scheduler.cron' is required.",
            flush=True
        )

        return False

    # ------------------------------------------------------------------
    # Sheet update
    # ------------------------------------------------------------------

    sheet_update = config.get(
        "sheet_update",
        {}
    )

    if sheet_update is None:
        sheet_update = {}

    if not isinstance(sheet_update, dict):
        print(
            "[ERROR] 'sheet_update' configuration is invalid.",
            flush=True
        )

        return False

    if not isinstance(sheet_update.get("enabled", False), bool):
        print(
            "[ERROR] 'sheet_update.enabled' must be true or false.",
            flush=True
        )

        return False

    if sheet_update.get("enabled", False):

        if not resolve_secret(
            sheet_update.get(
                "google_apps_secret",
                ""
            )
        ):
            print(
                "[ERROR] sheet_update.google_apps_secret "
                "is required when enabled.",
                flush=True
            )

            return False

        sheet_timeout = sheet_update.get(
            "timeout_seconds",
            timeout
        )

        if (
            not isinstance(sheet_timeout, (int, float))
            or sheet_timeout <= 0
        ):
            print(
                "[ERROR] 'sheet_update.timeout_seconds' "
                "must be greater than 0.",
                flush=True
            )

            return False

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    storage = config.get("storage")

    if not isinstance(storage, dict):
        print(
            "[ERROR] 'storage' configuration is missing or invalid.",
            flush=True
        )

        return False

    for storage_name in SUPPORTED_STORAGE_TYPES:

        storage_config = storage.get(
            storage_name
        )

        if storage_config is None:
            continue

        if not isinstance(storage_config, dict):
            print(
                f"[ERROR] Storage '{storage_name}' "
                "configuration is invalid.",
                flush=True
            )

            return False

        enabled = storage_config.get("enabled")

        if not isinstance(enabled, bool):
            print(
                f"[ERROR] Storage '{storage_name}' "
                "'enabled' must be true or false.",
                flush=True
            )

            return False

        expected_type = EXPECTED_TYPES[
            storage_name
        ]

        storage_type = storage_config.get(
            "type"
        )

        if storage_type != expected_type:
            print(
                f"[ERROR] Storage '{storage_name}' "
                f"has invalid type: {storage_type!r}. "
                f"Expected {expected_type!r}.",
                flush=True
            )

            return False

        output_mode = storage_config.get(
            "output_mode"
        )

        if output_mode not in OUTPUT_MODES[
            storage_name
        ]:
            allowed = ", ".join(
                sorted(
                    OUTPUT_MODES[
                        storage_name
                    ]
                )
            )

            print(
                f"[ERROR] Storage '{storage_name}' "
                f"has invalid output_mode: "
                f"{output_mode!r}. "
                f"Allowed values: {allowed}.",
                flush=True
            )

            return False

        # URL output requires a public web base URL.
        if output_mode == "url":

            base_url = storage_config.get(
                "base_url",
                ""
            ).strip()

            if not base_url:
                print(
                    f"[ERROR] Storage '{storage_name}' "
                    "requires 'base_url' when "
                    "output_mode is 'url'.",
                    flush=True
                )

                return False

        if not enabled:
            continue

        # --------------------------------------------------------------
        # Enabled storage-specific requirements
        # --------------------------------------------------------------

        if storage_name == "github":

            repository = storage_config.get(
                "repository",
                ""
            ).strip()

            token = storage_config.get(
                "token",
                ""
            )

            if not repository:
                print(
                    "[ERROR] github.repository is required.",
                    flush=True
                )

                return False

            if "/" not in repository:
                print(
                    "[ERROR] github.repository must be in "
                    "owner/repository form.",
                    flush=True
                )

                return False

            if not resolve_secret(token):
                print(
                    "[ERROR] github.token is required.",
                    flush=True
                )

                return False

        elif storage_name == "local":

            path = storage_config.get(
                "path",
                ""
            ).strip()

            if not path:
                print(
                    "[ERROR] local.path is required.",
                    flush=True
                )

                return False

        elif storage_name == "r2":

            endpoint = storage_config.get(
                "endpoint",
                ""
            ).strip()

            bucket = storage_config.get(
                "bucket",
                ""
            ).strip()

            access_key = storage_config.get(
                "access_key",
                ""
            ).strip()

            secret_key = storage_config.get(
                "secret_key",
                ""
            ).strip()

            if not endpoint:
                print(
                    "[ERROR] r2.endpoint is required.",
                    flush=True
                )

                return False

            if not bucket:
                print(
                    "[ERROR] r2.bucket is required.",
                    flush=True
                )

                return False

            if not access_key or not secret_key:
                print(
                    "[ERROR] r2 access_key and secret_key "
                    "are required.",
                    flush=True
                )

                return False

        elif storage_name == "s3":

            region = storage_config.get(
                "region",
                ""
            ).strip()

            bucket = storage_config.get(
                "bucket",
                ""
            ).strip()

            access_key = storage_config.get(
                "access_key",
                ""
            ).strip()

            secret_key = storage_config.get(
                "secret_key",
                ""
            ).strip()

            if not region:
                print(
                    "[ERROR] s3.region is required.",
                    flush=True
                )

                return False

            if not bucket:
                print(
                    "[ERROR] s3.bucket is required.",
                    flush=True
                )

                return False

            if not access_key or not secret_key:
                print(
                    "[ERROR] s3 access_key and secret_key "
                    "are required.",
                    flush=True
                )

                return False

    # ------------------------------------------------------------------
    # Primary storage
    # ------------------------------------------------------------------

    primary_storage = config.get(
        "primary_storage"
    )

    if primary_storage not in SUPPORTED_STORAGE_TYPES:
        print(
            f"[ERROR] Invalid primary_storage: "
            f"{primary_storage!r}. "
            f"Supported values: "
            f"{', '.join(sorted(SUPPORTED_STORAGE_TYPES))}",
            flush=True
        )

        return False

    primary_config = storage.get(
        primary_storage
    )

    if not isinstance(primary_config, dict):
        print(
            f"[ERROR] Primary storage '{primary_storage}' "
            "configuration is missing.",
            flush=True
        )

        return False

    if not primary_config.get(
        "enabled",
        False
    ):
        print(
            f"[ERROR] Primary storage '{primary_storage}' "
            "is disabled.",
            flush=True
        )

        return False

    return True


def load_config():

    if not CONFIG_FILE.exists():

        create_default_config()

        print(
            "[WARN] config.json not found.",
            flush=True
        )

        print(
            f"[INFO] Created default config: {CONFIG_FILE}",
            flush=True
        )

        print(
            "[WARN] Please edit config.json "
            "and restart container.",
            flush=True
        )

        return None

    try:

        with CONFIG_FILE.open(
            "r",
            encoding="utf-8"
        ) as f:

            config = json.load(f)

    except json.JSONDecodeError as e:

        print(
            f"[ERROR] Invalid config.json: {e}",
            flush=True
        )

        return None

    if not validate_config(
        config
    ):

        print(
            "[ERROR] Configuration validation failed.",
            flush=True
        )

        return None

    return config