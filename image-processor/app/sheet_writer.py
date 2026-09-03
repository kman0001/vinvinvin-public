import json
import os
import time
import uuid
from urllib.error import HTTPError
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
    urlopen,
)

from app.source import get_source_url


# ============================================================
# Apps Script updateStatus retry settings
# ============================================================

STATUS_MAX_RETRIES = 7

STATUS_RETRY_DELAYS = (
    10,
    20,
    30,
    60,
    120,
    300,
)

STATUS_RETRYABLE_HTTP_CODES = {
    404,
    429,
    500,
    502,
    503,
    504,
}


# ============================================================
# Redirect handler
# ============================================================

class NoRedirectHandler(HTTPRedirectHandler):

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None


# ============================================================
# Secret
# ============================================================

def _resolve_secret(
    value
):

    value = str(
        value or ""
    ).strip()

    if (
        value.startswith("${")
        and value.endswith("}")
    ):

        return os.environ.get(
            value[2:-1],
            "",
        )

    if value.startswith(
        "env:"
    ):

        return os.environ.get(
            value[4:],
            "",
        )

    return value


# ============================================================
# Update URL
# ============================================================

def _get_update_url(
    config
):

    sheet_config = config.get(
        "sheet_update",
        {}
    )

    url = sheet_config.get(
        "url",
        ""
    ).strip()

    if url:
        return url

    return get_source_url(
        config
    )


# ============================================================
# Status URL
# ============================================================

def _build_status_url(
    update_url,
    request_id,
):

    separator = (
        "&"
        if "?" in update_url
        else "?"
    )

    return (
        f"{update_url}"
        f"{separator}"
        f"action=updateStatus"
        f"&requestId={request_id}"
    )


# ============================================================
# Cleanup URL
# ============================================================

def _build_cleanup_url(
    update_url,
):

    separator = (
        "&"
        if "?" in update_url
        else "?"
    )

    return (
        f"{update_url}"
        f"{separator}"
        f"action=cleanupImageUpdates"
    )


# ============================================================
# Load Apps Script update status
# ============================================================

def _load_update_status(
    update_url,
    request_id,
    timeout,
):

    status_url = _build_status_url(
        update_url,
        request_id,
    )

    request = Request(
        status_url,
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "vinvinvin-image-processor/1.0"
            ),
        },
        method="GET",
    )

    try:

        with urlopen(
            request,
            timeout=timeout,
        ) as response:

            return json.load(
                response
            )

    except HTTPError as exc:

        if exc.code in STATUS_RETRYABLE_HTTP_CODES:

            print(
                "[WARN] Failed loading Apps Script "
                "update status",
                flush=True,
            )

            print(
                f"[WARN] Status: "
                f"{exc.code} {exc.reason}",
                flush=True,
            )

            return None

        print(
            "[ERROR] Apps Script update status "
            "failed",
            flush=True,
        )

        print(
            f"[ERROR] Status: "
            f"{exc.code} {exc.reason}",
            flush=True,
        )

        print(
            f"[ERROR] Status URL: "
            f"{status_url}",
            flush=True,
        )

        try:

            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            if body:

                print(
                    "[ERROR] Response body:",
                    flush=True,
                )

                print(
                    body[:5000],
                    flush=True,
                )

        except Exception:
            pass

        return {
            "ok": False,
            "pending": False,
            "error": (
                f"Apps Script update status "
                f"HTTP {exc.code}: {exc.reason}"
            ),
        }

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        print(
            "[WARN] Failed loading Apps Script "
            f"update status: {exc}",
            flush=True,
        )

        return None


# ============================================================
# Wait for Apps Script update status
# ============================================================

def _wait_for_update_status(
    update_url,
    request_id,
    timeout,
):

    last_result = None

    for attempt in range(
        STATUS_MAX_RETRIES
    ):

        result = _load_update_status(
            update_url,
            request_id,
            timeout,
        )

        if result is None:

            last_result = None

        else:

            last_result = result

            if not isinstance(
                result,
                dict,
            ):

                print(
                    "[ERROR] Invalid Apps Script "
                    f"update status response: {result!r}",
                    flush=True,
                )

                return None

            if result.get(
                "ok"
            ):

                return result

            if result.get(
                "pending"
            ) is True:

                print(
                    "[INFO] Apps Script update status "
                    "is still pending",
                    flush=True,
                )

            else:

                return result

        if attempt >= (
            STATUS_MAX_RETRIES - 1
        ):

            break

        delay = STATUS_RETRY_DELAYS[
            min(
                attempt,
                len(
                    STATUS_RETRY_DELAYS
                ) - 1,
            )
        ]

        print(
            "[INFO] Retrying Apps Script "
            "update status "
            f"({attempt + 1}/{STATUS_MAX_RETRIES}) "
            f"in {delay}s...",
            flush=True,
        )

        time.sleep(
            delay
        )

    print(
        "[ERROR] Apps Script update status "
        "failed after "
        f"{STATUS_MAX_RETRIES} attempts",
        flush=True,
    )

    return last_result


# ============================================================
# Cleanup stale image update properties
# ============================================================

def _cleanup_image_update_properties(
    config,
    timeout,
):

    sheet_config = config.get(
        "sheet_update",
        {}
    )

    secret = _resolve_secret(
        sheet_config.get(
            "google_apps_secret",
            "",
        )
    )

    if not secret:

        print(
            "[WARN] Google Apps secret is not configured; "
            "skipping image update property cleanup",
            flush=True,
        )

        return False

    update_url = _get_update_url(
        config
    )

    cleanup_url = _build_cleanup_url(
        update_url
    )

    payload = {
        "action": "cleanupImageUpdates",
        "googleAppsSecret": secret,
    }

    request = Request(
        cleanup_url,
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "vinvinvin-image-processor/1.0"
            ),
        },
        method="POST",
    )

    opener = build_opener(
        NoRedirectHandler()
    )

    try:

        with opener.open(
            request,
            timeout=timeout,
        ) as response:

            result = json.load(
                response
            )

            if not isinstance(
                result,
                dict,
            ):

                print(
                    "[WARN] Invalid Apps Script "
                    "cleanup response",
                    flush=True,
                )

                return False

            if not result.get(
                "ok"
            ):

                print(
                    "[WARN] Failed cleaning up "
                    "image update properties: "
                    f"{result.get('error', 'unknown error')}",
                    flush=True,
                )

                return False

            print(
                "[INFO] Image update properties cleanup completed: "
                f"{result.get('deleted', 0)} deleted",
                flush=True,
            )

            return True

    except HTTPError as exc:

        if exc.code in (
            301,
            302,
            303,
            307,
            308,
        ):

            print(
                "[INFO] Apps Script cleanup request "
                "completed with redirect response",
                flush=True,
            )

            return True

        print(
            "[WARN] Apps Script image update "
            "property cleanup failed",
            flush=True,
        )

        print(
            f"[WARN] Status: "
            f"{exc.code} {exc.reason}",
            flush=True,
        )

        return False

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        print(
            "[WARN] Failed cleaning up Apps Script "
            f"image update properties: {exc}",
            flush=True,
        )

        return False


# ============================================================
# Write image destinations to Google Sheet
# ============================================================

def write_sheet_destinations(
    config,
    rows,
    clear_rows=None,
):
    """
    Google Sheet 이미지 열을 업데이트한다.

    이미지 열은 config.json의
    sheet_update.image_column 값을 사용한다.

    반환값:

        True
            Sheet 업데이트가 성공했거나
            업데이트할 필요가 없는 정상 상태.

        False
            Sheet 업데이트가 실패했거나
            성공 여부를 확인하지 못한 상태.

    호출자는 True를 받은 경우에만
    cache.json을 저장해야 한다.
    """

    clear_rows = clear_rows or []

    sheet_config = config.get(
        "sheet_update",
        {}
    )

    if not sheet_config.get(
        "enabled",
        False,
    ):

        print(
            "[INFO] Google Sheet update disabled",
            flush=True,
        )

        return True

    if not rows and not clear_rows:

        print(
            "[INFO] No sheet image destinations "
            "to update",
            flush=True,
        )

        return True

    image_column = str(
        sheet_config.get(
            "image_column",
            "",
        )
    ).strip()

    if not image_column:

        print(
            "[ERROR] sheet_update.image_column "
            "is not configured",
            flush=True,
        )

        return False

    update_url = _get_update_url(
        config
    )

    request_id = uuid.uuid4().hex

    payload = {
        "action": "updateImages",

        "requestId": request_id,

        "googleAppsSecret": _resolve_secret(
            sheet_config.get(
                "google_apps_secret",
                "",
            )
        ),

        "imageColumn": image_column,

        "rows": rows,

        "clearRows": clear_rows,
    }

    timeout = sheet_config.get(
        "timeout_seconds",
        config.get(
            "source",
            {}
        ).get(
            "timeout_seconds",
            30,
        ),
    )

    request = Request(
        update_url,
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": (
                "vinvinvin-image-processor/1.0"
            ),
        },
        method="POST",
    )

    opener = build_opener(
        NoRedirectHandler()
    )

    post_completed = False

    # ========================================================
    # POST updateImages
    #
    # POST 자체는 한 번만 실행한다.
    # ========================================================

    try:

        with opener.open(
            request,
            timeout=timeout,
        ) as response:

            result = json.load(
                response
            )

            if isinstance(
                result,
                dict,
            ):

                post_completed = True

                if not result.get(
                    "ok"
                ):

                    print(
                        "[ERROR] Failed updating "
                        "Google Sheet images: "
                        f"{result.get('error', 'unknown error')}",
                        flush=True,
                    )

                    return False

            else:

                print(
                    "[ERROR] Invalid Google Apps Script "
                    "updateImages response",
                    flush=True,
                )

                return False

    except HTTPError as exc:

        if exc.code in (
            301,
            302,
            303,
            307,
            308,
        ):

            post_completed = True

            print(
                "[INFO] Google Apps Script "
                "image update request completed "
                "(redirect response)",
                flush=True,
            )

        else:

            print(
                "[ERROR] Google Apps Script "
                "HTTP error",
                flush=True,
            )

            print(
                f"[ERROR] Status: "
                f"{exc.code} {exc.reason}",
                flush=True,
            )

            print(
                f"[ERROR] Request URL: "
                f"{update_url}",
                flush=True,
            )

            print(
                f"[ERROR] Response URL: "
                f"{exc.url}",
                flush=True,
            )

            try:

                body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )

                if body:

                    print(
                        "[ERROR] Response body:",
                        flush=True,
                    )

                    print(
                        body[:5000],
                        flush=True,
                    )

            except Exception:
                pass

            return False

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        print(
            "[ERROR] Failed updating Google "
            f"Sheet images: {exc}",
            flush=True,
        )

        return False

    if not post_completed:

        return False

    # ========================================================
    # updateStatus 확인
    # ========================================================

    print(
        "[INFO] Checking Apps Script JSON "
        "response",
        flush=True,
    )

    result = _wait_for_update_status(
        update_url,
        request_id,
        timeout,
    )

    if result is None:

        print(
            "[ERROR] Could not confirm Google "
            "Sheet image update status",
            flush=True,
        )

        return False

    if not isinstance(
        result,
        dict,
    ):

        print(
            "[ERROR] Invalid Apps Script "
            f"update status response: {result!r}",
            flush=True,
        )

        return False

    if not result.get(
        "ok"
    ):

        print(
            "[ERROR] Failed updating Google "
            "Sheet images: "
            f"{result.get('error', 'unknown error')}",
            flush=True,
        )

        return False

    # ========================================================
    # Sheet 업데이트 성공
    # ========================================================

    print(
        "[INFO] Apps Script JSON response "
        "confirmed",
        flush=True,
    )

    print(
        "[INFO] Google Sheet image "
        "destinations updated: "
        f"{result.get('updated', 0)} updated, "
        f"{result.get('skipped', 0)} skipped",
        flush=True,
    )

    print(
        "[INFO] Google Sheet image "
        "destinations were submitted "
        "successfully",
        flush=True,
    )

    # ========================================================
    # 잔여 image_update_* property 정리
    # ========================================================

    _cleanup_image_update_properties(
        config,
        timeout,
    )

    return True