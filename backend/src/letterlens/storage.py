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


