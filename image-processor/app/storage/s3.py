from pathlib import Path

from app.storage.base import Storage


class S3Storage(Storage):
    """S3-compatible storage for AWS S3 and Cloudflare R2."""

    def __init__(
        self,
        config,
        name="s3"
    ):
        super().__init__(
            config
        )

        try:
            import boto3
        except ImportError as exc:
            raise ValueError(
                "boto3 is required for S3/R2 storage"
            ) from exc

        self.bucket = config.get(
            "bucket",
            ""
        ).strip()

        self.prefix = config.get(
            "path",
            ""
        ).strip().strip(
            "/"
        )

        self.output_mode = config.get(
            "output_mode",
            "filename"
        )

        self.base_url = config.get(
            "base_url",
            ""
        ).rstrip(
            "/"
        )

        access_key = config.get(
            "access_key",
            ""
        ).strip()

        secret_key = config.get(
            "secret_key",
            ""
        ).strip()

        if not self.bucket:
            raise ValueError(
                f"{name}.bucket is required"
            )

        if not access_key or not secret_key:
            raise ValueError(
                f"{name} access credentials are required"
            )

        if (
            self.output_mode == "url"
            and not self.base_url
        ):
            raise ValueError(
                f"{name}.base_url is required "
                "when output_mode=url"
            )

        kwargs = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }

        region = config.get(
            "region",
            ""
        ).strip()

        endpoint = config.get(
            "endpoint",
            ""
        ).strip()

        if region:
            kwargs[
                "region_name"
            ] = region

        if endpoint:
            kwargs[
                "endpoint_url"
            ] = endpoint

        self.client = boto3.client(
            "s3",
            **kwargs
        )

    def _key(
        self,
        destination
    ):
        return "/".join(
            part
            for part in (
                self.prefix,
                destination.strip(
                    "/"
                )
            )
            if part
        )

    def _get_public_url(
        self,
        destination
    ):
        if self.output_mode != "url":
            return None

        return (
            f"{self.base_url}/"
            f"{self._key(destination)}"
        )

    def upload(
        self,
        source: Path,
        destination: str
    ):
        content_type = (
            "image/webp"
            if destination.lower().endswith(
                ".webp"
            )
            else "image/jpeg"
        )

        self.client.upload_file(
            str(
                source
            ),
            self.bucket,
            self._key(
                destination
            ),
            ExtraArgs={
                "ContentType": content_type
            },
        )

        return {
            "path": destination,
            "url": self._get_public_url(
                destination
            )
        }

    def delete(
        self,
        destination: str
    ):
        self.client.delete_object(
            Bucket=self.bucket,
            Key=self._key(
                destination
            )
        )

    def exists(
        self,
        destination: str
    ):
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=self._key(
                    destination
                )
            )

            return True

        except self.client.exceptions.ClientError as exc:
            status_code = exc.response.get(
                "ResponseMetadata",
                {}
            ).get(
                "HTTPStatusCode"
            )

            if status_code == 404:
                return False

            raise

    def download(
        self,
        source,
        destination
    ):
        self.client.download_file(
            self.bucket,
            self._key(
                source
            ),
            str(
                destination
            )
        )