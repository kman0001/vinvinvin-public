from datetime import datetime
from pathlib import Path

from app.cache.cache import CacheManager
from app.processor.operation import UploadOperation


def now():
    return datetime.now().astimezone().isoformat()


class SyncEngine:

    def __init__(
        self,
        storages,
        primary_storage=None
    ):
        self.cache = CacheManager()
        self.storages = storages
        self.primary_storage = primary_storage

    # ============================================================
    # Cache
    # ============================================================

    def get_cached_item(
        self,
        key
    ):
        return self.cache.get(
            key
        )

    def save_cache(
        self
    ):
        """
        현재 메모리에 있는 cache 상태를
        실제 cache.json에 저장한다.

        Google Sheet 업데이트가 성공적으로 확인된
        이후에 호출해야 한다.
        """

        self.cache.save()

    # ============================================================
    # Storage
    # ============================================================

    def _get_storage(
        self,
        storage_name
    ):
        for name, storage in self.storages:

            if name == storage_name:
                return storage

        return None

    # ============================================================
    # Storage configuration
    # ============================================================

    def _get_storage_config(
        self,
        storage
    ):
        config = getattr(
            storage,
            "config",
            {}
        )

        if not isinstance(
            config,
            dict
        ):
            return {}

        return config

    def _get_output_mode(
        self,
        storage
    ):
        config = self._get_storage_config(
            storage
        )

        mode = config.get(
            "output_mode",
            "filename"
        )

        if mode not in {
            "filename",
            "url"
        }:
            return "filename"

        return mode

    # ============================================================
    # Primary destination
    # ============================================================

    def get_primary_destination(
        self,
        filename
    ):
        """
        현재 config의 primary storage 설정을 기준으로
        현재 시점의 Sheet destination을 계산한다.

        중요:
        cache에 저장되어 있던 destination은 사용하지 않는다.

        filename mode:
            filename

        url mode:
            base_url + "/" + filename
        """

        if not filename:
            return None

        primary_storage = (
            self.primary_storage
        )

        if not primary_storage:
            return None

        storage = self._get_storage(
            primary_storage
        )

        if storage is None:
            return None

        config = self._get_storage_config(
            storage
        )

        output_mode = config.get(
            "output_mode",
            "filename"
        )

        if output_mode == "url":

            base_url = config.get(
                "base_url",
                ""
            ).rstrip(
                "/"
            )

            if base_url:

                return (
                    f"{base_url}/"
                    f"{str(filename).lstrip('/')}"
                )

        return filename

    # ============================================================
    # Existing file helpers
    # ============================================================

    def _get_cached_filename(
        self,
        item
    ):
        if not isinstance(
            item,
            dict
        ):
            return None

        filename = item.get(
            "filename"
        )

        if not filename:
            return None

        return Path(
            str(filename)
        ).name

    # ============================================================
    # Reusable image
    # ============================================================

    def _filename_contains_hash(
        self,
        filename,
        image_hash
    ):
        if not filename:
            return False

        if not image_hash:
            return False

        filename = Path(
            filename
        ).name

        stem = Path(
            filename
        ).stem

        return stem.endswith(
            image_hash
        )

    def find_reusable_image(
        self,
        image_hash
    ):
        if not image_hash:
            return None

        for key in self.cache.keys():

            item = self.cache.get(
                key
            )

            if not item:
                continue

            filename = item.get(
                "filename"
            )

            if not self._filename_contains_hash(
                filename,
                image_hash
            ):
                continue

            storage_modes = item.get(
                "storage",
                {}
            )

            if not isinstance(
                storage_modes,
                dict
            ):
                continue

            for storage_name in storage_modes:

                storage = self._get_storage(
                    storage_name
                )

                if storage is None:
                    continue

                path = self._get_cached_filename(
                    item
                )

                if not path:
                    continue

                try:

                    if not storage.exists(
                        path
                    ):
                        continue

                except Exception:
                    continue

                print(
                    "[INFO] Reusable image found: "
                    f"{storage_name}/{path}",
                    flush=True
                )

                return {
                    "storage_name": storage_name,
                    "storage": storage,
                    "path": path,
                    "source_item": item
                }

        return None

    def export_reusable_image(
        self,
        reusable,
        temp_dir
    ):
        storage = reusable[
            "storage"
        ]

        path = reusable[
            "path"
        ]

        output = (
            Path(temp_dir)
            / Path(path).name
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        storage.download(
            path,
            output
        )

        print(
            "[INFO] Exported reusable image: "
            f"{output.name}",
            flush=True
        )

        return output

    # ============================================================
    # Skip
    # ============================================================

    def skip_item(
        self,
        key,
        category,
        name,
        cached_item
    ):
        """
        이미 Sheet와 현재 destination이 일치한
        cache v3 항목은 기존 정보를 유지한다.

        Sheet 업데이트가 성공하면 cache를 다시 저장하기 때문에
        updated_at만 현재 시각으로 갱신한다.
        """

        item = dict(
            cached_item
        )

        item.update(
            {
                "category": category,
                "name": name,
                "updated_at": now()
            }
        )

        self.cache.set(
            key,
            item
        )

        return item

    # ============================================================
    # Synced item
    # ============================================================

    def _set_synced_item(
        self,
        key,
        category,
        name,
        filename,
        storage_status,
        primary_storage=None
    ):
        """
        cache v3 형태로 동기화 결과를 저장한다.

        primary:
            "github"

        storage:
            {
                "github": "filename",
                "local": "filename"
            }
        """

        primary_name = (
            primary_storage
            or self.primary_storage
        )

        if not primary_name:
            return None

        if primary_name not in storage_status:
            return None

        item = {
            "category": category,
            "name": name,
            "filename": filename,
            "primary": primary_name,
            "storage": dict(
                storage_status
            ),
            "updated_at": now()
        }

        self.cache.set(
            key,
            item
        )

        return item

    # ============================================================
    # Upload
    # ============================================================

    def execute_upload(
        self,
        operation,
        previous_item
    ):
        """
        모든 enabled storage에 동일한 filename으로
        결과를 동기화한다.

        반환값은 cache v3의 storage 부분과 동일한 형태다.

            {
                "github": "filename",
                "local": "filename"
            }

        실패한 storage는 결과에서 제외한다.
        """

        previous_filename = (
            self._get_cached_filename(
                previous_item
            )
        )

        storage_modes = {}

        for (
            storage_name,
            storage
        ) in self.storages:

            try:

                # ------------------------------------------------
                # 현재 filename이 이미 존재하면 재사용
                # ------------------------------------------------

                if (
                    previous_filename
                    == operation.destination
                    and storage.exists(
                        operation.destination
                    )
                ):

                    storage_modes[
                        storage_name
                    ] = self._get_output_mode(
                        storage
                    )

                    print(
                        "[INFO] Reused existing image: "
                        f"{storage_name}/"
                        f"{operation.destination}",
                        flush=True
                    )

                    continue

                # ------------------------------------------------
                # 이전 filename이 다르면 기존 파일 삭제
                # ------------------------------------------------

                if (
                    previous_filename
                    and previous_filename
                    != operation.destination
                ):

                    try:

                        if storage.exists(
                            previous_filename
                        ):

                            storage.delete(
                                previous_filename
                            )

                            print(
                                "[INFO] Removed old image: "
                                f"{storage_name}/"
                                f"{previous_filename}",
                                flush=True
                            )

                    except Exception as exc:

                        print(
                            "[WARN] Failed removing old image: "
                            f"{storage_name}/"
                            f"{previous_filename}: "
                            f"{exc}",
                            flush=True
                        )

                # ------------------------------------------------
                # Upload
                # ------------------------------------------------

                storage.upload(
                    operation.source,
                    operation.destination
                )

                storage_modes[
                    storage_name
                ] = self._get_output_mode(
                    storage
                )

            except Exception as exc:

                print(
                    "[ERROR] Storage upload failed: "
                    f"{storage_name}: {exc}",
                    flush=True
                )

        return storage_modes

    def sync_item(
        self,
        key,
        category,
        name,
        filename,
        output
    ):
        previous_item = self.cache.get(
            key
        ) or {}

        operation = UploadOperation(
            key=key,
            source=output,
            destination=filename
        )

        storage_modes = self.execute_upload(
            operation=operation,
            previous_item=previous_item
        )

        # --------------------------------------------------------
        # 모든 enabled storage가 성공해야 cache에 기록한다.
        # --------------------------------------------------------

        expected_storages = {
            name
            for name, _ in self.storages
        }

        actual_storages = set(
            storage_modes.keys()
        )

        if actual_storages != expected_storages:

            print(
                "[ERROR] Not all storage operations "
                "completed successfully",
                flush=True
            )

            return None

        return self._set_synced_item(
            key=key,
            category=category,
            name=name,
            filename=filename,
            storage_status=storage_modes,
            primary_storage=self.primary_storage
        )

    # ============================================================
    # Delete
    # ============================================================

    def execute_delete(
        self,
        storage_name,
        storage,
        path
    ):
        if not path:
            return

        if self._is_url(path):
            return

        try:

            if not storage.exists(
                path
            ):
                return

            storage.delete(
                path
            )

            print(
                "[INFO] Deleted stale image: "
                f"{storage_name}/{path}",
                flush=True
            )

        except Exception as exc:

            print(
                "[ERROR] Failed deleting stale image "
                f"{storage_name}/{path}: {exc}",
                flush=True
            )

    # ============================================================
    # Remove stale cache items
    # ============================================================

    def remove_stale_items(
        self,
        current_keys
    ):
        stale_keys = (
            self.cache.keys()
            - current_keys
        )

        active_paths = set()

        # --------------------------------------------------------
        # 현재 메뉴에서 사용하는 파일
        # --------------------------------------------------------

        for key in current_keys:

            item = self.cache.get(
                key
            )

            if not item:
                continue

            filename = (
                self._get_cached_filename(
                    item
                )
            )

            if not filename:
                continue

            storage_modes = item.get(
                "storage",
                {}
            )

            if not isinstance(
                storage_modes,
                dict
            ):
                continue

            for storage_name in storage_modes:

                active_paths.add(
                    (
                        storage_name,
                        filename
                    )
                )

        # --------------------------------------------------------
        # 메뉴에서 삭제된 cache item 처리
        # --------------------------------------------------------

        for key in stale_keys:

            item = self.cache.get(
                key
            ) or {}

            filename = (
                self._get_cached_filename(
                    item
                )
            )

            if filename:

                storage_modes = item.get(
                    "storage",
                    {}
                )

                if isinstance(
                    storage_modes,
                    dict
                ):

                    for (
                        storage_name,
                        _mode
                    ) in storage_modes.items():

                        if (
                            storage_name,
                            filename
                        ) in active_paths:

                            continue

                        storage = self._get_storage(
                            storage_name
                        )

                        if storage is None:
                            continue

                        self.execute_delete(
                            storage_name,
                            storage,
                            filename
                        )

            self.cache.remove(
                key
            )

    # ============================================================
    # Storage flush
    # ============================================================

    def flush_storages(
        self
    ):
        for (
            storage_name,
            storage
        ) in self.storages:

            try:

                storage.flush()

            except Exception as exc:

                raise RuntimeError(
                    f"Failed flushing storage "
                    f"'{storage_name}': {exc}"
                ) from exc

    # ============================================================
    # URL helper
    # ============================================================

    def _is_url(
        self,
        value
    ):
        return (
            isinstance(
                value,
                str
            )
            and (
                value.startswith(
                    "http://"
                )
                or value.startswith(
                    "https://"
                )
            )
        )