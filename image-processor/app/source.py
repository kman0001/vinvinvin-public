import json
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse, urlencode, parse_qsl, urlunparse
from urllib.request import Request, urlopen


DEFAULT_CONSTANTS_PATH = "/js/config/constants.js"

API_EXPORT_RE = re.compile(
    r"export\s+const\s+API\s*=\s*([\"'])(?P<url>https?://.+?)\1\s*;",
    re.DOTALL,
)

# Apps Script JSON 요청 재시도 설정
MAX_APPS_SCRIPT_RETRIES = 3
APPS_SCRIPT_RETRY_DELAY_SECONDS = 2

VISIBLE_TEXT_RE = re.compile(
    r"[\s\u00A0\u2000-\u200D\u202F\u205F\u3000\u3164\uFEFF]"
)


def has_visible_text(value: object) -> bool:
    return VISIBLE_TEXT_RE.sub("", str(value or "")) != ""


class SourceError(RuntimeError):
    """Raised when the website source cannot be used."""


@dataclass(frozen=True, slots=True)
class MenuImage:
    category: str
    name: str
    photo: str

    @property
    def is_url(self) -> bool:
        return urlparse(self.photo).scheme in {"http", "https"}

    @property
    def is_local_webp(self) -> bool:
        return (
            not self.is_url
            and self.photo.split("?", 1)[0].lower().endswith(".webp")
        )


def parse_apps_script_url(
    constants_source: str,
    label: str = "constants.js",
) -> str:
    match = API_EXPORT_RE.search(constants_source)

    if not match:
        raise SourceError(
            f"Could not find export const API in {label}."
        )

    return match.group("url").strip()


def build_constants_url(
    base_url: str,
    constants_path: str = DEFAULT_CONSTANTS_PATH,
) -> str:
    base_url = base_url.strip()
    constants_path = (
        constants_path.strip()
        or DEFAULT_CONSTANTS_PATH
    )

    if not base_url:
        raise SourceError(
            "source.base_url is required."
        )

    if urlparse(base_url).scheme not in {"http", "https"}:
        raise SourceError(
            "source.base_url must start with http:// or https://."
        )

    return urljoin(
        base_url.rstrip("/") + "/",
        constants_path.lstrip("/"),
    )


def get_source_url(config: dict) -> str:
    source_config = config.get("source", {})

    constants_url = build_constants_url(
        source_config.get("base_url", ""),
        source_config.get(
            "constants_path",
            DEFAULT_CONSTANTS_PATH,
        ),
    )

    timeout = source_config.get(
        "timeout_seconds",
        30,
    )

    request = Request(
        constants_url,
        headers={
            "Accept": "application/javascript,text/javascript,text/plain,*/*",
            "User-Agent": "vinvinvin-image-processor/1.0",
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            source = response.read().decode("utf-8")

    except (OSError, UnicodeDecodeError) as exc:
        raise SourceError(
            f"Could not load website constants URL: {constants_url}"
        ) from exc

    return parse_apps_script_url(
        source,
        constants_url,
    )


def parse_menu(
    payload: object,
    image_column: str,
) -> tuple[list[MenuImage], list[dict]]:
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("menu"), list)
    ):
        raise SourceError(
            "Apps Script JSON must contain a menu array."
        )

    items = []
    clear_rows = []

    for index, row in enumerate(payload["menu"]):
        if not isinstance(row, dict):
            continue

        category = str(
            row.get("항목", "")
        ).strip()

        name = str(
            row.get("이름", "")
        ).strip()

        photo = str(
            row.get(image_column, "")
        ).strip()

        category_visible = has_visible_text(category)
        name_visible = has_visible_text(name)
        photo_visible = has_visible_text(photo)

        if not category_visible and name_visible and photo_visible:
            clear_rows.append(
                {
                    "category": "",
                    "name": name,
                }
            )

            print(
                f"[INFO] menu[{index}] has no 항목; "
                f"clearing {image_column} for {name}.",
                flush=True,
            )
            continue

        if not (category_visible and name_visible and photo_visible):
            print(
                f"[WARN] menu[{index}] lacks 항목, 이름, or "
                f"{image_column}; skipped.",
                flush=True,
            )
            continue

        items.append(
            MenuImage(
                category=category,
                name=name,
                photo=photo,
            )
        )

    return items, clear_rows


def build_image_processor_url(url: str, lang: str = "ko") -> str:
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["action"] = "imageProcessor"
    query["lang"] = lang
    return urlunparse(
        parts._replace(query=urlencode(query))
    )


def load_menu(config: dict) -> tuple[list[MenuImage], list[dict]]:
    source_config = config.get("source", {})

    sheet_config = config.get(
        "sheet_update",
        {},
    )

    image_column = str(
        sheet_config.get(
            "image_column",
            "",
        )
    ).strip()

    if not image_column:
        raise SourceError(
            "sheet_update.image_column is required."
        )

    url = build_image_processor_url(
        get_source_url(config)
    )

    timeout = source_config.get(
        "timeout_seconds",
        30,
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "vinvinvin-image-processor/1.0",
        },
    )

    last_error = None

    for attempt in range(
        1,
        MAX_APPS_SCRIPT_RETRIES + 1,
    ):

        try:

            with urlopen(
                request,
                timeout=timeout,
            ) as response:

                payload = json.load(response)

            # 성공하면 즉시 기존 처리로 진행
            return parse_menu(
                payload,
                image_column,
            )

        except HTTPError as exc:

            last_error = exc

            # 최초 에러부터 사용자에게 표시
            print(
                f"[ERROR] Could not load Apps Script JSON: {exc}",
                flush=True,
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:

            last_error = exc

            # 네트워크 오류나 JSON 응답 오류도 표시
            print(
                f"[ERROR] Could not load Apps Script JSON: {exc}",
                flush=True,
            )

        # 마지막 시도였다면 더 이상 재시도하지 않음
        if attempt >= MAX_APPS_SCRIPT_RETRIES:
            break

        print(
            "[INFO] Retrying Apps Script JSON load "
            f"({attempt}/{MAX_APPS_SCRIPT_RETRIES})...",
            flush=True,
        )

        time.sleep(
            APPS_SCRIPT_RETRY_DELAY_SECONDS
        )

    raise SourceError(
        f"Could not load Apps Script JSON: {last_error}"
    ) from last_error