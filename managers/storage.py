"""S3-compatible storage backend for publishing assets.

Targets any S3-compatible object store — AWS S3, MinIO, and self-hosted
instances such as RustFS. Selected via ``COMFY_MCP_PUBLISH_BACKEND=s3``; the
default local-filesystem backend lives in ``publish_manager.py``.

``boto3`` is an optional dependency: it is imported lazily so the local backend
keeps working without it. Install with ``uv sync --group s3`` (or ``pip install
boto3``) to enable S3 publishing.
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("MCP_Server")


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean-ish environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class S3Config:
    """Configuration for the S3-compatible publish backend.

    For RustFS / MinIO you typically set ``endpoint_url`` (e.g.
    ``http://localhost:9000``) and keep ``force_path_style=True`` (the default),
    since those servers expect path-style addressing rather than the
    virtual-host style AWS uses.
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        prefix: str = "gen/",
        public_base_url: Optional[str] = None,
        force_path_style: bool = True,
        acl: Optional[str] = None,
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url or None
        self.region = region or "us-east-1"
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key

        # Normalize prefix to "" or "something/" (no leading slash, trailing slash).
        prefix = (prefix or "").lstrip("/")
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        self.prefix = prefix

        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self.force_path_style = force_path_style
        self.acl = acl or None

    @classmethod
    def from_env(cls) -> Optional["S3Config"]:
        """Build an S3Config from environment variables.

        Returns None if no bucket is configured (so the caller can fall back to
        a clear "not configured" error rather than constructing a half-config).
        """
        bucket = os.getenv("COMFY_MCP_S3_BUCKET")
        if not bucket:
            return None
        return cls(
            bucket=bucket,
            endpoint_url=os.getenv("COMFY_MCP_S3_ENDPOINT_URL"),
            region=os.getenv("COMFY_MCP_S3_REGION", "us-east-1"),
            # Fall back to standard AWS_* credentials if the namespaced ones are unset.
            access_key_id=os.getenv("COMFY_MCP_S3_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("COMFY_MCP_S3_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
            prefix=os.getenv("COMFY_MCP_S3_PREFIX", "gen/"),
            public_base_url=os.getenv("COMFY_MCP_S3_PUBLIC_BASE_URL"),
            force_path_style=_env_bool("COMFY_MCP_S3_FORCE_PATH_STYLE", True),
            acl=os.getenv("COMFY_MCP_S3_ACL"),
        )


class S3StorageBackend:
    """Uploads published assets to an S3-compatible bucket.

    The boto3 client is created lazily on first use so that importing this
    module (and constructing the backend) never requires boto3 to be installed.
    """

    def __init__(self, config: S3Config):
        self.config = config
        self._client = None
        self._bucket_ok: Optional[bool] = None

    @property
    def client(self):
        """Lazily construct and cache the boto3 S3 client."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config as BotoConfig
            except ImportError as e:
                raise RuntimeError(
                    "boto3 is required for the S3 publish backend but is not installed. "
                    "Install it with `uv sync --group s3` or `pip install boto3`."
                ) from e

            addressing_style = "path" if self.config.force_path_style else "auto"
            self._client = boto3.client(
                "s3",
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                config=BotoConfig(
                    signature_version="s3v4",
                    s3={"addressing_style": addressing_style},
                ),
            )
        return self._client

    def key_for(self, filename: str) -> str:
        """Compute the object key for a published filename (prefix + filename)."""
        return f"{self.config.prefix}{filename}"

    def object_url(self, key: str) -> str:
        """Compute a browser-facing URL for an object key.

        Priority:
        1. Explicit ``public_base_url`` (e.g. a CDN in front of the bucket).
        2. Path-style URL against a custom ``endpoint_url`` (RustFS / MinIO).
        3. AWS virtual-host URL.
        """
        if self.config.public_base_url:
            return f"{self.config.public_base_url}/{key}"
        if self.config.endpoint_url:
            return f"{self.config.endpoint_url.rstrip('/')}/{self.config.bucket}/{key}"
        return f"https://{self.config.bucket}.s3.{self.config.region}.amazonaws.com/{key}"

    def exists(self, filename: str) -> bool:
        """Return True if an object already exists for this filename."""
        from botocore.exceptions import ClientError

        key = self.key_for(filename)
        try:
            self.client.head_object(Bucket=self.config.bucket, Key=key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def put_bytes(
        self,
        filename: str,
        data: bytes,
        content_type: str,
        overwrite: bool = True,
    ) -> Dict[str, str]:
        """Upload bytes under the configured prefix.

        Returns a dict with the object ``key``, browser ``url``, and ``uri``
        (``s3://bucket/key``).
        """
        key = self.key_for(filename)
        if not overwrite and self.exists(filename):
            raise ValueError(
                f"Object already exists and overwrite=False: s3://{self.config.bucket}/{key}"
            )

        extra: Dict[str, Any] = {"ContentType": content_type}
        if self.config.acl:
            extra["ACL"] = self.config.acl

        self.client.put_object(Bucket=self.config.bucket, Key=key, Body=data, **extra)
        logger.info(f"Uploaded s3://{self.config.bucket}/{key} ({len(data)} bytes)")
        return {
            "key": key,
            "url": self.object_url(key),
            "uri": f"s3://{self.config.bucket}/{key}",
        }

    def get_json(self, filename: str) -> Dict[str, Any]:
        """Fetch and parse a JSON object, returning {} if it does not exist."""
        from botocore.exceptions import ClientError

        key = self.key_for(filename)
        try:
            resp = self.client.get_object(Bucket=self.config.bucket, Key=key)
            body = resp["Body"].read()
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey", "NotFound"):
                return {}
            raise
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse JSON object {key}, treating as empty: {e}")
            return {}

    def ensure_ready(self) -> Tuple[bool, Optional[str]]:
        """Verify the bucket is reachable and credentials work.

        The result is cached after the first success so repeated readiness
        checks don't make a network round-trip every time.
        """
        if self._bucket_ok:
            return True, None
        try:
            from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
        except ImportError:
            return False, (
                "boto3 is not installed. Install it with `uv sync --group s3` or `pip install boto3`."
            )

        try:
            self.client.head_bucket(Bucket=self.config.bucket)
            self._bucket_ok = True
            return True, None
        except (ClientError, BotoCoreError, NoCredentialsError) as e:
            return False, str(e)
        except RuntimeError as e:  # boto3 not installed (raised by .client)
            return False, str(e)

    def describe(self) -> Dict[str, Any]:
        """Return a non-secret summary of the backend for status/info tools."""
        return {
            "backend": "s3",
            "bucket": self.config.bucket,
            "endpoint_url": self.config.endpoint_url,
            "region": self.config.region,
            "prefix": self.config.prefix,
            "force_path_style": self.config.force_path_style,
            "public_base_url": self.config.public_base_url,
            "acl": self.config.acl,
            "example_url": self.object_url(self.key_for("example.webp")),
        }
