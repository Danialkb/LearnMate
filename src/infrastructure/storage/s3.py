from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from configs.env import Settings


@dataclass(frozen=True, slots=True)
class S3ObjectInfo:
    bucket: str
    key: str
    etag: str | None = None


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        if not settings.S3_ACCESS_KEY_ID:
            raise ValueError("S3_ACCESS_KEY_ID is required")
        if not settings.S3_SECRET_ACCESS_KEY:
            raise ValueError("S3_SECRET_ACCESS_KEY is required")
        if not settings.STORAGE_BUCKET_NAME:
            raise ValueError("STORAGE_BUCKET_NAME is required")

        self._settings = settings
        self._session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
        self._client_config = Config(
            s3={"addressing_style": "path" if settings.S3_USE_PATH_STYLE else "virtual"}
        )

    @staticmethod
    def _sanitize_key_part(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
        normalized = normalized.strip("._-")
        return normalized or "file"

    def generate_document_object_key(
        self,
        *,
        document_id: UUID,
        filename: str,
        namespace: str = "materials",
        created_at: datetime | None = None,
    ) -> str:
        timestamp = created_at or datetime.now(UTC)
        safe_filename = self._sanitize_key_part(filename)
        random_prefix = uuid4().hex[:8]
        return (
            f"{self._sanitize_key_part(namespace)}/"
            f"{timestamp:%Y/%m/%d}/"
            f"documents/{document_id}/"
            f"{random_prefix}_{safe_filename}"
        )

    @property
    def bucket_name(self) -> str:
        bucket_name = self._settings.STORAGE_BUCKET_NAME
        if bucket_name is None:
            raise ValueError("STORAGE_BUCKET_NAME is required")
        return bucket_name

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[Any]:
        async with self._session.client(
            "s3",
            endpoint_url=self._settings.S3_ENDPOINT_URL,
            config=self._client_config,
        ) as client:
            yield client

    async def ensure_bucket_exists(self) -> None:
        async with self._client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket_name)
            except ClientError as exc:
                error_code = str(exc.response.get("Error", {}).get("Code", ""))
                if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise

                await client.create_bucket(Bucket=self.bucket_name)

    async def upload_file(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> S3ObjectInfo:
        await self.ensure_bucket_exists()

        put_object_kwargs: dict[str, object] = {
            "Bucket": self.bucket_name,
            "Key": key,
            "Body": data,
        }
        if content_type:
            put_object_kwargs["ContentType"] = content_type

        async with self._client() as client:
            response = await client.put_object(**put_object_kwargs)

        return S3ObjectInfo(
            bucket=self.bucket_name,
            key=key,
            etag=str(response.get("ETag")) if response.get("ETag") else None,
        )

    async def get_file(self, *, key: str) -> bytes:
        async with self._client() as client:
            response = await client.get_object(Bucket=self.bucket_name, Key=key)
            body = response["Body"]
            data = await body.read()
            return bytes(data)

    async def delete_file(self, *, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=key)
