import io
import os
from pathlib import Path

from PIL import Image, ImageFilter
from rembg import new_session, remove


TARGET_HEIGHT = 800

REMBG_SESSION = None


def get_rembg_session():
    """
    rembg 모델 lazy loading.

    최초 배경 제거 시 모델을 로딩하고,
    이후 같은 컨테이너에서는 메모리를 재사용한다.
    """

    global REMBG_SESSION

    if REMBG_SESSION is None:

        model_home = os.getenv(
            "U2NET_HOME",
            "/tmp/u2net"
        )

        os.environ[
            "U2NET_HOME"
        ] = model_home

        print(
            "[IMAGE PROCESS] loading rembg model",
            flush=True
        )

        REMBG_SESSION = new_session(
            "u2net"
        )

        print(
            "[IMAGE PROCESS] rembg model ready",
            flush=True
        )

    return REMBG_SESSION


def has_transparency(
    image: Image.Image
) -> bool:

    if "A" not in image.getbands():
        return False

    alpha = image.getchannel(
        "A"
    )

    alpha_min, _ = alpha.getextrema()

    return alpha_min < 255


def crop_to_alpha_bounds(
    image: Image.Image
) -> Image.Image:

    if "A" not in image.getbands():
        return image

    alpha = image.getchannel(
        "A"
    )

    bbox = alpha.getbbox()

    if not bbox:
        return image

    return image.crop(
        bbox
    )


def resize_to_800(
    image: Image.Image
) -> Image.Image:
    """
    이미지 높이를 정확히 800px로 맞춘다.

    800px보다 작은 이미지도 확대한다.
    """

    object_height = image.height

    if object_height <= 0:
        return image

    if object_height == TARGET_HEIGHT:
        return image

    scale = (
        TARGET_HEIGHT
        / object_height
    )

    new_size = (
        round(
            image.width * scale
        ),
        TARGET_HEIGHT
    )

    resized = image.resize(
        new_size,
        Image.Resampling.LANCZOS
    )

    if scale > 1:
        return resized.filter(
            ImageFilter.UnsharpMask(
                radius=1.0,
                percent=120,
                threshold=3
            )
        )

    return resized


def convert_result_to_image(
    result
) -> Image.Image:

    if isinstance(
        result,
        Image.Image
    ):
        return result

    with Image.open(
        io.BytesIO(
            result
        )
    ) as image:

        image.load()

        return image.convert(
            "RGBA"
        )


def process_image(
    source: Path,
    category: str,
    output_dir: Path,
    filename: str
) -> Path:

    with Image.open(
        source
    ) as opened:

        opened.load()

        image = opened.convert(
            "RGBA"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    transparent = has_transparency(
        image
    )

    if (
        category != "안주"
        and not transparent
    ):

        result = remove(
            image,
            session=get_rembg_session()
        )

        image = convert_result_to_image(
            result
        )

    image = crop_to_alpha_bounds(
        image
    )

    image = resize_to_800(
        image
    )

    if image.mode not in {
        "RGB",
        "RGBA"
    }:
        image = image.convert(
            "RGBA"
        )

    destination = (
        output_dir
        / filename
    )

    image.save(
        destination,
        format="WEBP",
        quality=90,
        method=6
    )

    return destination