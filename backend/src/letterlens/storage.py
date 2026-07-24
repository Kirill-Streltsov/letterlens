"""Letter images in S3: pre-signed uploads and downloads, and deletion.

Images are optional. The pipeline works on the OCR lines that the client sends.
Images are uploaded only after the user agrees, so that a counsellor can see the
original. The bucket encrypts at rest and expires objects after the retention period.
"""

from __future__ import annotations

from typing import Any, Protocol

MAX_IMAGE_BYTES = 8 * 1024 * 1024
URL_TTL_SECONDS = 600


class ImageStorage(Protocol):
    enabled: bool

    def upload_targets(self, owner_id: str, letter_id: str, count: int) -> list[dict[str, Any]]: ...

    def download_url(self, key: str) -> str: ...

    def delete(self, keys: list[str]) -> None: ...


class DisabledStorage:
    enabled = False

    def upload_targets(self, owner_id: str, letter_id: str, count: int) -> list[dict[str, Any]]:
        return []

    def download_url(self, key: str) -> str:
        raise RuntimeError("image storage is disabled")

    def delete(self, keys: list[str]) -> None:
        return None


class S3Storage:
    enabled = True

    def __init__(self, bucket: str, region: str, client: Any = None) -> None:
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3", region_name=region, config=Config(signature_version="s3v4")
            )
        self.client = client
        self.bucket = bucket

    @staticmethod
    def key_for(owner_id: str, letter_id: str, n: int) -> str:
        return f"letters/{owner_id}/{letter_id}/{n}.jpg"

