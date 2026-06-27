"""Tests for the S3-compatible publish backend.

These tests never touch the network or require boto3: URL derivation is pure,
and the PublishManager S3 paths are exercised with an in-memory fake backend.

Run with pytest from project root:
    pytest tests/test_publish_s3.py -v
"""

import json

import pytest

from managers.publish_manager import PublishConfig, PublishManager
from managers.storage import S3Config, S3StorageBackend


class TestS3Config:
    """Tests for S3Config construction and env parsing."""

    def test_prefix_normalization(self):
        assert S3Config(bucket="b", prefix="gen").prefix == "gen/"
        assert S3Config(bucket="b", prefix="/gen/").prefix == "gen/"
        assert S3Config(bucket="b", prefix="").prefix == ""
        assert S3Config(bucket="b", prefix="a/b").prefix == "a/b/"

    def test_from_env_requires_bucket(self, monkeypatch):
        monkeypatch.delenv("COMFY_MCP_S3_BUCKET", raising=False)
        assert S3Config.from_env() is None

    def test_from_env_parses_values(self, monkeypatch):
        monkeypatch.setenv("COMFY_MCP_S3_BUCKET", "assets")
        monkeypatch.setenv("COMFY_MCP_S3_ENDPOINT_URL", "http://localhost:9000")
        monkeypatch.setenv("COMFY_MCP_S3_PREFIX", "renders")
        monkeypatch.setenv("COMFY_MCP_S3_FORCE_PATH_STYLE", "true")
        monkeypatch.setenv("COMFY_MCP_S3_ACCESS_KEY_ID", "key")
        monkeypatch.setenv("COMFY_MCP_S3_SECRET_ACCESS_KEY", "secret")

        cfg = S3Config.from_env()
        assert cfg.bucket == "assets"
        assert cfg.endpoint_url == "http://localhost:9000"
        assert cfg.prefix == "renders/"
        assert cfg.force_path_style is True
        assert cfg.access_key_id == "key"
        assert cfg.secret_access_key == "secret"

    def test_from_env_falls_back_to_aws_creds(self, monkeypatch):
        monkeypatch.setenv("COMFY_MCP_S3_BUCKET", "assets")
        monkeypatch.delenv("COMFY_MCP_S3_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("COMFY_MCP_S3_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")

        cfg = S3Config.from_env()
        assert cfg.access_key_id == "aws-key"
        assert cfg.secret_access_key == "aws-secret"


class TestObjectUrl:
    """URL derivation is pure and does not construct a boto3 client."""

    def test_public_base_url_wins(self):
        backend = S3StorageBackend(S3Config(
            bucket="b", prefix="gen/", endpoint_url="http://localhost:9000",
            public_base_url="https://cdn.example.com",
        ))
        assert backend.object_url("gen/hero.webp") == "https://cdn.example.com/gen/hero.webp"

    def test_path_style_endpoint(self):
        backend = S3StorageBackend(S3Config(
            bucket="assets", prefix="gen/", endpoint_url="http://localhost:9000",
        ))
        assert backend.object_url("gen/hero.webp") == "http://localhost:9000/assets/gen/hero.webp"

    def test_aws_virtual_host(self):
        backend = S3StorageBackend(S3Config(bucket="assets", region="eu-west-1", prefix="gen/"))
        assert backend.object_url("gen/hero.webp") == "https://assets.s3.eu-west-1.amazonaws.com/gen/hero.webp"

    def test_key_for_applies_prefix(self):
        backend = S3StorageBackend(S3Config(bucket="b", prefix="gen/"))
        assert backend.key_for("hero.webp") == "gen/hero.webp"


class FakeS3Backend:
    """In-memory stand-in for S3StorageBackend used to exercise PublishManager."""

    def __init__(self, prefix="gen/", bucket="assets"):
        self.prefix = prefix
        self.bucket = bucket
        self.objects = {}  # key -> bytes
        self.ready = True

    def key_for(self, filename):
        return f"{self.prefix}{filename}"

    def object_url(self, key):
        return f"http://localhost:9000/{self.bucket}/{key}"

    def exists(self, filename):
        return self.key_for(filename) in self.objects

    def put_bytes(self, filename, data, content_type, overwrite=True):
        key = self.key_for(filename)
        if not overwrite and key in self.objects:
            raise ValueError(f"Object already exists and overwrite=False: s3://{self.bucket}/{key}")
        self.objects[key] = data
        return {"key": key, "url": self.object_url(key), "uri": f"s3://{self.bucket}/{key}"}

    def get_json(self, filename):
        key = self.key_for(filename)
        if key not in self.objects:
            return {}
        return json.loads(self.objects[key])

    def ensure_ready(self):
        return (True, None) if self.ready else (False, "bucket unreachable")

    def describe(self):
        return {"backend": "s3", "bucket": self.bucket, "prefix": self.prefix}


def _make_s3_manager(tmp_path, fake=None):
    """Build a PublishManager wired to a fake S3 backend, with a local source dir."""
    output_root = tmp_path / "comfyui" / "output"
    output_root.mkdir(parents=True)

    config = PublishConfig(
        project_root=tmp_path,
        comfyui_output_root=output_root,
        backend="s3",
        s3_config=S3Config(bucket="assets", prefix="gen/", endpoint_url="http://localhost:9000"),
    )
    manager = PublishManager(config)
    manager.s3 = fake or FakeS3Backend()
    return manager, output_root


class TestPublishManagerS3:
    """PublishManager behavior when backend='s3'."""

    def test_s3_config_skips_local_publish_root(self, tmp_path):
        config = PublishConfig(
            project_root=tmp_path,
            backend="s3",
            s3_config=S3Config(bucket="assets"),
        )
        # No public/gen directory should be created for the S3 backend.
        assert config.publish_root is None
        assert not (tmp_path / "public" / "gen").exists()

    def test_store_asset_uploads_bytes(self, tmp_path):
        manager, output_root = _make_s3_manager(tmp_path)
        (output_root / "test.png").write_bytes(b"raw png bytes")

        source_path = manager.resolve_source_path("", "test.png")
        result = manager.store_asset(source_path, "hero.png", asset_id="a1")

        assert result["dest_url"] == "http://localhost:9000/assets/gen/hero.png"
        assert result["dest_path"] == "s3://assets/gen/hero.png"
        assert result["mime_type"] == "image/png"
        assert manager.s3.objects["gen/hero.png"] == b"raw png bytes"

    def test_store_asset_no_overwrite_conflict(self, tmp_path):
        fake = FakeS3Backend()
        fake.objects["gen/hero.png"] = b"existing"
        manager, output_root = _make_s3_manager(tmp_path, fake=fake)
        (output_root / "test.png").write_bytes(b"new")

        source_path = manager.resolve_source_path("", "test.png")
        with pytest.raises(ValueError, match="overwrite=False"):
            manager.store_asset(source_path, "hero.png", overwrite=False)

    @pytest.mark.skipif(not pytest.importorskip("PIL", reason="Pillow not available"), reason="Pillow required")
    def test_store_asset_web_optimize_to_webp(self, tmp_path):
        from PIL import Image

        manager, output_root = _make_s3_manager(tmp_path)
        Image.new("RGB", (256, 256), "blue").save(output_root / "test.png", "PNG")

        source_path = manager.resolve_source_path("", "test.png")
        result = manager.store_asset(
            source_path, "hero.webp", asset_id="a1", web_optimize=True, max_bytes=100_000
        )

        assert result["mime_type"] == "image/webp"
        assert result["compression_info"]["compressed"] is True
        assert "gen/hero.webp" in manager.s3.objects

    def test_update_manifest_read_modify_write(self, tmp_path):
        manager, _ = _make_s3_manager(tmp_path)

        manager.update_manifest("hero", "hero.webp")
        manager.update_manifest("logo", "logo.png")

        manifest = json.loads(manager.s3.objects["gen/manifest.json"])
        assert manifest == {"hero": "hero.webp", "logo": "logo.png"}

    def test_ensure_ready_when_configured(self, tmp_path):
        output_root = tmp_path / "comfyui" / "output"
        output_root.mkdir(parents=True)
        (output_root / "ComfyUI_00001.png").write_text("x")

        config = PublishConfig(
            project_root=tmp_path,
            comfyui_output_root=output_root,
            backend="s3",
            s3_config=S3Config(bucket="assets"),
        )
        manager = PublishManager(config)
        manager.s3 = FakeS3Backend()

        is_ready, error_code, _ = manager.ensure_ready()
        assert is_ready is True
        assert error_code is None

    def test_ensure_ready_not_configured(self, tmp_path):
        config = PublishConfig(project_root=tmp_path, backend="s3", s3_config=None)
        manager = PublishManager(config)  # self.s3 stays None

        is_ready, error_code, info = manager.ensure_ready()
        assert is_ready is False
        assert error_code == "S3_BACKEND_NOT_CONFIGURED"
        assert "COMFY_MCP_S3_BUCKET" in info["message"]

    def test_get_publish_info_reports_backend(self, tmp_path):
        output_root = tmp_path / "comfyui" / "output"
        output_root.mkdir(parents=True)
        (output_root / "ComfyUI_00001.png").write_text("x")

        config = PublishConfig(
            project_root=tmp_path,
            comfyui_output_root=output_root,
            backend="s3",
            s3_config=S3Config(bucket="assets"),
        )
        manager = PublishManager(config)
        manager.s3 = FakeS3Backend()

        info = manager.get_publish_info()
        assert info["backend"] == "s3"
        assert info["publish_root"] is None
        assert info["s3"]["bucket"] == "assets"
