import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from app.processor.hash import (
    calculate_hash,
    calculate_menu_hash,
)
from app.processor.image import process_image
from app.processor.sync_engine import SyncEngine
from app.sheet_writer import write_sheet_destinations
from app.source import SourceError, load_menu
from app.storage import create_storage
from app.cache.pending import PendingManager


LOCAL_IMAGE_DIR = Path(
    "/app/images"
)


def get_category_prefix(
    category,
    category_map
):
    return category_map.get(
        category,
        "Other"
    )


def get_primary_storage(
    config
):
    return config.get(
        "primary_storage"
    )


def get_enabled_storages(
    config
):
    storages = []

    for (
        name,
        storage_config
    ) in config.get(
        "storage",
        {}
    ).items():

        if not storage_config.get(
            "enabled",
            False
        ):
            continue

        try:

            storage = create_storage(
                name,
                storage_config
            )

            storages.append(
                (
                    name,
                    storage
                )
            )

        except (
            KeyError,
            ValueError
        ) as exc:

            print(
                f"[ERROR] Storage {name} is unavailable: {exc}",
                flush=True
            )

    return storages


def download(
    url,
    destination,
    timeout
):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "vinvinvin-image-processor/1.0"
            )
        }
    )

    with urlopen(
        request,
        timeout=timeout
    ) as response:

        with destination.open(
            "wb"
        ) as output:

            shutil.copyfileobj(
                response,
                output
            )


def find_local_image(
    filename
):
    if not filename:
        return None

    filename = Path(
        filename
    ).name

    source = (
        LOCAL_IMAGE_DIR
        / filename
    )

    if source.is_file():
        return source

    return None


def is_ignored_image(
    filename
):
    if not filename:
        return False

    return Path(
        filename
    ).name.lower().startswith(
        "no-image"
    )


# ============================================================
# Cache / Destination helpers
# ============================================================

def can_skip_item(
    cached_item,
    item,
    sync_engine
):
    """
    현재 Google Sheet의 item.photo와
    현재 config + cache filename으로 계산한
    primary destination이 동일한 경우에만 skip한다.

    중요:
    cache에 과거에 기록된 primary destination은
    전혀 사용하지 않는다.
    """

    if not cached_item:
        return False

    filename = cached_item.get(
        "filename"
    )

    if not filename:
        return False

    destination = (
        sync_engine.get_primary_destination(
            filename
        )
    )

    if not destination:
        return False

    return item.photo == destination


def process_local_source(
    source,
    temp_dir
):
    local_source = (
        temp_dir
        / "source"
    )

    shutil.copy2(
        source,
        local_source
    )

    return local_source


# ============================================================
# Pending helpers
# ============================================================

def _build_pending_item(
    result
):
    """
    pending.json에는 cache v3와 동일한
    처리 결과를 저장한다.

    pending은 Sheet 업데이트가 완료되지 않은
    상태이므로 cache에 아직 확정하지 않는다.
    """

    return {
        "category": result.get(
            "category"
        ),
        "name": result.get(
            "name"
        ),
        "filename": result.get(
            "filename"
        ),
        "primary": result.get(
            "primary"
        ),
        "storage": result.get(
            "storage",
            {}
        )
    }


def _pending_to_cache_item(
    pending_item
):
    """
    pending v1 item을 cache v3 item으로 변환한다.
    """

    return {
        "category": pending_item.get(
            "category"
        ),
        "name": pending_item.get(
            "name"
        ),
        "filename": pending_item.get(
            "filename"
        ),
        "primary": pending_item.get(
            "primary"
        ),
        "storage": pending_item.get(
            "storage",
            {}
        ),
        "updated_at": datetime.now(
            timezone.utc
        ).astimezone().isoformat()
    }


def _pending_to_sheet_update(
    pending_item,
    sync_engine
):
    """
    pending의 filename을 기준으로
    현재 config의 primary destination을 다시 계산한다.

    pending에 저장된 destination은 사용하지 않는다.
    """

    filename = pending_item.get(
        "filename"
    )

    if not filename:
        return None

    destination = (
        sync_engine.get_primary_destination(
            filename
        )
    )

    if not destination:
        return None

    return {
        "category": pending_item.get(
            "category"
        ),
        "name": pending_item.get(
            "name"
        ),
        "destination": destination
    }


# ============================================================
# Main processing
# ============================================================

def process_images(
    config
):
    print(
        "Image processing started",
        flush=True
    )

    category_map = config.get(
        "category_map",
        {}
    )

    # ========================================================
    # Storage 초기화
    # ========================================================

    storages = get_enabled_storages(
        config
    )

    if not storages:

        print(
            "[ERROR] No enabled storage found",
            flush=True
        )

        return

    # ========================================================
    # Menu 로드
    # ========================================================

    try:

        menu, clear_rows = load_menu(
            config
        )

    except SourceError as exc:

        print(
            f"[ERROR] {exc}",
            flush=True
        )

        return

    timeout = config.get(
        "source",
        {}
    ).get(
        "timeout_seconds",
        30
    )

    # ========================================================
    # Primary storage
    # ========================================================

    primary_storage = get_primary_storage(
        config
    )

    if (
        not primary_storage
        or not any(
            name == primary_storage
            for name, _ in storages
        )
    ):

        primary_storage = storages[0][0]

    sync_engine = SyncEngine(
        storages,
        primary_storage
    )

    pending_manager = PendingManager()

    current_keys = set()
    sheet_updates = []

    # ========================================================
    # Pending 상태 출력
    # ========================================================

    if not pending_manager.is_empty():

        print(
            "[INFO] Pending items found: "
            f"{len(pending_manager.keys())}",
            flush=True
        )

        print(
            "[INFO] Pending items will be "
            "processed before new image processing",
            flush=True
        )

    # ========================================================
    # Menu processing
    # ========================================================

    for index, item in enumerate(
        menu
    ):

        # ====================================================
        # 필수 데이터 확인
        # ====================================================

        if (
            not item.category
            or not item.name
            or not item.photo
        ):

            print(
                f"[WARN] menu[{index}] lacks "
                "항목, 이름, or 사진; skipped.",
                flush=True
            )

            continue

        # ====================================================
        # Placeholder image 제외
        # ====================================================

        if is_ignored_image(
            item.photo
        ):

            print(
                f"[INFO] Ignored placeholder image: "
                f"{item.photo}",
                flush=True
            )

            continue

        # ====================================================
        # 메뉴 항목 key
        # ====================================================

        menu_hash = calculate_menu_hash(
            item.category,
            item.name
        )

        current_keys.add(
            menu_hash
        )

        # ====================================================
        # Pending 우선 처리
        # ====================================================

        pending_item = pending_manager.get(
            menu_hash
        )

        if pending_item:

            print(
                "[INFO] Pending item found: "
                f"{item.name}",
                flush=True
            )

            print(
                "[INFO] Reusing completed storage "
                "result without reprocessing: "
                f"{item.name}",
                flush=True
            )

            # ------------------------------------------------
            # pending → 메모리 cache
            # ------------------------------------------------

            sync_engine.cache.set(
                menu_hash,
                _pending_to_cache_item(
                    pending_item
                )
            )

            sheet_update = (
                _pending_to_sheet_update(
                    pending_item,
                    sync_engine
                )
            )

            if sheet_update:

                sheet_updates.append(
                    sheet_update
                )

            else:

                print(
                    "[ERROR] Pending item has no "
                    "valid primary destination: "
                    f"{item.name}",
                    flush=True
                )

            continue

        # ====================================================
        # 기존 cache 확인
        # ====================================================

        cached_item = sync_engine.get_cached_item(
            menu_hash
        )

        # ====================================================
        # 이미 처리된 항목
        # ====================================================

        if can_skip_item(
            cached_item,
            item,
            sync_engine
        ):

            result = sync_engine.skip_item(
                key=menu_hash,
                category=item.category,
                name=item.name,
                cached_item=cached_item
            )

            destination = (
                sync_engine.get_primary_destination(
                    result.get(
                        "filename"
                    )
                )
            )

            if destination:

                sheet_updates.append(
                    {
                        "category": item.category,
                        "name": item.name,
                        "destination": destination
                    }
                )

            print(
                "[INFO] Skipped already processed image: "
                f"{item.name}",
                flush=True
            )

            continue

        try:

            with tempfile.TemporaryDirectory(
                prefix="image-processor-"
            ) as temporary_directory:

                temp_dir = Path(
                    temporary_directory
                )

                source = (
                    temp_dir
                    / "source"
                )

                # ====================================================
                # Source 확보
                # ====================================================

                if item.is_url:

                    print(
                        f"[INFO] Downloading: "
                        f"{item.name}",
                        flush=True
                    )

                    download(
                        item.photo,
                        source,
                        timeout
                    )

                else:

                    local_source = find_local_image(
                        item.photo
                    )

                    if local_source is None:

                        print(
                            "[ERROR] Local image not found: "
                            f"{item.photo}",
                            flush=True
                        )

                        continue

                    print(
                        "[INFO] Using local image: "
                        f"{item.name} <- "
                        f"{local_source.name}",
                        flush=True
                    )

                    process_local_source(
                        local_source,
                        temp_dir
                    )

                # ====================================================
                # 원본 이미지 hash
                # ====================================================

                image_hash = calculate_hash(
                    source
                )

                filename = (
                    f"{get_category_prefix(item.category, category_map)}_"
                    f"{image_hash}.webp"
                )

                # ====================================================
                # 동일 원본 이미지의
                # 기존 처리 결과 확인
                # ====================================================

                reusable = (
                    sync_engine.find_reusable_image(
                        image_hash
                    )
                )

                if reusable:

                    print(
                        "[INFO] Reusing processed image: "
                        f"{filename}",
                        flush=True
                    )

                    output = (
                        sync_engine.export_reusable_image(
                            reusable,
                            temp_dir
                        )
                    )

                else:

                    output = process_image(
                        source,
                        item.category,
                        temp_dir,
                        filename
                    )

                # ====================================================
                # Storage 동기화
                # ====================================================

                result = sync_engine.sync_item(
                    key=menu_hash,
                    category=item.category,
                    name=item.name,
                    filename=filename,
                    output=output
                )

                # ====================================================
                # 처리 결과
                # ====================================================

                if result:

                    destination = (
                        sync_engine.get_primary_destination(
                            result.get(
                                "filename"
                            )
                        )
                    )

                    if destination:

                        sheet_updates.append(
                            {
                                "category": item.category,
                                "name": item.name,
                                "destination": destination
                            }
                        )

                    print(
                        "[INFO] Processed: "
                        f"{item.name} -> "
                        f"{filename}",
                        flush=True
                    )

                else:

                    print(
                        "[ERROR] Processing failed: "
                        f"{item.name}",
                        flush=True
                    )

        except Exception as exc:

            print(
                f"[ERROR] Failed to process "
                f"{item.name}: {exc}",
                flush=True
            )

    # ========================================================
    # 메뉴에서 삭제된 항목 처리
    # ========================================================

    sync_engine.remove_stale_items(
        current_keys
    )

    # ========================================================
    # Storage batch flush
    # ========================================================

    try:

        sync_engine.flush_storages()

    except Exception as exc:

        print(
            "[ERROR] Storage flush failed: "
            f"{exc}",
            flush=True
        )

        print(
            "[ERROR] Google Sheet update skipped",
            flush=True
        )

        print(
            "[ERROR] cache.json was not saved",
            flush=True
        )

        return

    print(
        "[INFO] All storage operations completed successfully",
        flush=True
    )

    # ========================================================
    # Pending 저장
    # ========================================================

    pending_saved_keys = []

    for sheet_update in sheet_updates:

        category = sheet_update.get(
            "category"
        )

        name = sheet_update.get(
            "name"
        )

        if not category or not name:
            continue

        key = calculate_menu_hash(
            category,
            name
        )

        result = sync_engine.get_cached_item(
            key
        )

        if not result:
            continue

        pending_item = _build_pending_item(
            result
        )

        pending_manager.set(
            key,
            pending_item
        )

        pending_saved_keys.append(
            key
        )

    # ========================================================
    # pending.json 저장
    # ========================================================

    if pending_saved_keys:

        try:

            pending_manager.save()

            print(
                "[INFO] pending.json saved successfully: "
                f"{len(pending_saved_keys)} item(s)",
                flush=True
            )

        except Exception as exc:

            print(
                "[ERROR] Failed saving pending.json: "
                f"{exc}",
                flush=True
            )

            print(
                "[ERROR] Google Sheet update skipped",
                flush=True
            )

            print(
                "[ERROR] cache.json was not saved",
                flush=True
            )

            return

    # ========================================================
    # Google Sheet 이미지 주소 업데이트
    #
    # Storage
    #     ↓
    # Storage flush
    #     ↓
    # pending.json
    #     ↓
    # Sheet
    #     ↓
    # cache.json
    # ========================================================

    sheet_update_success = (
        write_sheet_destinations(
            config,
            sheet_updates,
            clear_rows
        )
    )

    if not sheet_update_success:

        print(
            "[ERROR] Google Sheet update was not confirmed",
            flush=True
        )

        print(
            "[INFO] Processed images are preserved "
            "in pending.json",
            flush=True
        )

        print(
            "[INFO] The next execution will retry "
            "the Sheet update without reprocessing images",
            flush=True
        )

        print(
            "[ERROR] cache.json was not saved",
            flush=True
        )

        return

    # ========================================================
    # Cache 저장
    # ========================================================

    try:

        sync_engine.save_cache()

    except Exception as exc:

        print(
            "[ERROR] Failed saving cache.json: "
            f"{exc}",
            flush=True
        )

        print(
            "[WARN] pending.json will be kept "
            "for recovery",
            flush=True
        )

        return

    print(
        "[INFO] cache.json saved successfully",
        flush=True
    )

    # ========================================================
    # Pending 삭제
    # ========================================================

    try:

        for key in pending_saved_keys:

            pending_manager.remove(
                key
            )

        if pending_manager.is_empty():

            pending_manager.delete_file()

            print(
                "[INFO] pending.json removed successfully",
                flush=True
            )

        else:

            pending_manager.save()

            print(
                "[INFO] Remaining pending items preserved",
                flush=True
            )

    except Exception as exc:

        print(
            "[ERROR] Failed clearing pending.json: "
            f"{exc}",
            flush=True
        )

        print(
            "[WARN] cache.json was saved successfully, "
            "but pending.json was preserved for safety",
            flush=True
        )

        return

    print(
        "Image processing finished",
        flush=True
    )