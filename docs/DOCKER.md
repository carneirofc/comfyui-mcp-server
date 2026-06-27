# Running with Docker

A prebuilt, **feature-complete** image is published to the GitHub Container
Registry on every push to `main`:

```
ghcr.io/carneirofc/comfyui-mcp-server:latest
```

The image is hardened (slim Python base, dependencies from the frozen
`uv.lock`, no build tools, runs as a non-root user) and bundles **all optional
dependency groups** — including `boto3` for the S3 publish backend — so every
backend and tool group works out of the box, gated only by runtime env vars.
Images are also tagged by commit SHA (`sha-<short>`) and, for releases, by
version (`vX.Y.Z`).

## Contents

- [Prerequisite](#prerequisite)
- [Quick run](#quick-run)
- [Configuration (env vars)](#configuration-env-vars)
- [Optional tool groups](#optional-tool-groups)
- [Publishing to a local directory](#publishing-to-a-local-directory)
- [Publishing to S3 / MinIO / RustFS](#publishing-to-s3--minio--rustfs)
- [RustFS via docker-compose (complete example)](#rustfs-via-docker-compose-complete-example)
- [Custom workflows](#custom-workflows)
- [Build locally](#build-locally)
- [Security note](#security-note)

---

## Prerequisite

ComfyUI must be running and reachable **from inside the container**. The server
checks ComfyUI on startup and exits if it can't connect.

## Quick run

**Bash (Linux / macOS):**

```bash
docker run --rm \
  -p 9000:9000 \
  -e COMFYUI_URL=http://host.docker.internal:8188 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/carneirofc/comfyui-mcp-server:latest
```

**PowerShell (Windows):**

```powershell
docker run --rm `
  -p 9000:9000 `
  -e COMFYUI_URL=http://host.docker.internal:8188 `
  ghcr.io/carneirofc/comfyui-mcp-server:latest
```

- `-p 9000:9000` publishes the MCP endpoint at `http://127.0.0.1:9000/mcp`.
- `COMFYUI_URL` points the server at your ComfyUI instance. `host.docker.internal`
  resolves to the Docker host; the `--add-host` flag is required on **Linux**
  (it's automatic with Docker Desktop on macOS/Windows).
- If ComfyUI runs in another container on the same Docker network, use that
  service name instead, e.g. `-e COMFYUI_URL=http://comfyui:8188` (and drop the
  `--add-host`).
- To map to a different **host** port, change the left side of `-p` (e.g.
  `-p 9999:9000` serves at `http://127.0.0.1:9999/mcp`). To change the
  **container** port, set `-e COMFY_MCP_PORT=<port>` and match the right side of
  `-p`; the in-container healthcheck honors `COMFY_MCP_PORT` automatically.

Connect a client exactly as in the main [README](../README.md#use-with-an-ai-agent-cursor--claude--n8n)
— the endpoint is identical.

## Configuration (env vars)

Every environment variable from the main
[Configuration](../README.md#configuration) works via `-e`. The most common:

| Variable | Default (in image) | Description |
| --- | --- | --- |
| `COMFYUI_URL` | `http://host.docker.internal:8188` | ComfyUI base URL |
| `COMFY_MCP_HOST` | `0.0.0.0` | HTTP bind address. The image sets `0.0.0.0` so the published port is reachable |
| `COMFY_MCP_PORT` | `9000` | HTTP transport port inside the container |
| `COMFY_MCP_ASSET_TTL_HOURS` | `24` | Asset registry TTL |
| `COMFY_MCP_WORKFLOW_DIR` | `/app/workflows` | Workflow JSON directory |
| `COMFY_MCP_FEATURES` | (none) | Comma list of optional tool groups, or `all` (see below) |
| `COMFYUI_OUTPUT_ROOT` | (auto-detected) | ComfyUI output dir — publish **source** |
| `COMFY_MCP_PROJECT_ROOT` | (auto-detected) | Web project root — local publish **target** base |
| `COMFY_MCP_PUBLISH_ROOT` | (derived) | Exact local publish dir; overrides `…/public/gen` |
| `COMFY_MCP_PUBLISH_BACKEND` | `local` | `s3` to publish to S3/MinIO/RustFS instead of disk |
| `COMFY_MCP_S3_*` | — | S3 backend settings (see [Publishing to S3](#publishing-to-s3--minio--rustfs)) |

## Optional tool groups

The core tools are always available; additional groups are **off by default** to
keep the tool list (and the LLM's context) lean. Enable them with
`COMFY_MCP_FEATURES` — a comma/space list of group names, or `all`:

```bash
-e COMFY_MCP_FEATURES=all
-e COMFY_MCP_FEATURES=models,system
```

Groups: `models`, `nodes`, `upload`, `system`, `jobs_api`. See the main
[README → Optional Tool Groups](../README.md#optional-tool-groups-feature-flags)
for what each adds. The image bundles the dependencies for all of them.

## Publishing to a local directory

Outside Docker the publish tools auto-detect paths from the working directory;
inside a container that isn't meaningful, so set the **container** paths
explicitly and mount the corresponding host directories. The ComfyUI output is
the publish **source** (mount read-only); the project is the **target** (mount
writable).

**Bash (Linux / macOS):**

```bash
docker run --rm \
  -p 9000:9000 \
  -e COMFYUI_URL=http://host.docker.internal:8188 \
  -e COMFYUI_OUTPUT_ROOT=/comfy/output \
  -e COMFY_MCP_PROJECT_ROOT=/project \
  -v /path/to/ComfyUI/output:/comfy/output:ro \
  -v /path/to/your/project:/project \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/carneirofc/comfyui-mcp-server:latest
```

**PowerShell (Windows):**

```powershell
docker run --rm `
  -p 9000:9000 `
  -e COMFYUI_URL=http://host.docker.internal:8188 `
  -e COMFYUI_OUTPUT_ROOT=/comfy/output `
  -e COMFY_MCP_PROJECT_ROOT=/project `
  -v C:\path\to\ComfyUI\output:/comfy/output:ro `
  -v C:\path\to\your\project:/project `
  ghcr.io/carneirofc/comfyui-mcp-server:latest
```

With `COMFY_MCP_PROJECT_ROOT=/project`, published files land in
`/project/public/gen`. Set `COMFY_MCP_PUBLISH_ROOT` to target an exact dir.

## Publishing to S3 / MinIO / RustFS

The image already includes `boto3`, so you only set env vars. The publish
**source** is still the local ComfyUI output directory (mount it read-only); only
the **target** moves to object storage.

**Bash (Linux / macOS):**

```bash
docker run --rm \
  -p 9000:9000 \
  -e COMFYUI_URL=http://host.docker.internal:8188 \
  -e COMFYUI_OUTPUT_ROOT=/comfy/output \
  -e COMFY_MCP_PUBLISH_BACKEND=s3 \
  -e COMFY_MCP_S3_ENDPOINT_URL=http://host.docker.internal:9000 \
  -e COMFY_MCP_S3_BUCKET=comfy-assets \
  -e COMFY_MCP_S3_ACCESS_KEY_ID=rustfsadmin \
  -e COMFY_MCP_S3_SECRET_ACCESS_KEY=rustfsadmin \
  -e COMFY_MCP_S3_PUBLIC_BASE_URL=http://localhost:9000/comfy-assets \
  -v /path/to/ComfyUI/output:/comfy/output:ro \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/carneirofc/comfyui-mcp-server:latest
```

| `COMFY_MCP_S3_*` var | Notes |
| --- | --- |
| `COMFY_MCP_S3_BUCKET` | **Required.** Bucket must already exist |
| `COMFY_MCP_S3_ENDPOINT_URL` | S3 endpoint; omit for AWS. Use `http://host.docker.internal:9000` to reach a host-side MinIO/RustFS |
| `COMFY_MCP_S3_ACCESS_KEY_ID` / `COMFY_MCP_S3_SECRET_ACCESS_KEY` | Credentials (fall back to `AWS_*`) |
| `COMFY_MCP_S3_PREFIX` | Key prefix (default `gen/`) |
| `COMFY_MCP_S3_PUBLIC_BASE_URL` | URL **clients** use to fetch assets (the returned `dest_url`) |
| `COMFY_MCP_S3_FORCE_PATH_STYLE` | `true` (default) — required for MinIO/RustFS |
| `COMFY_MCP_S3_ACL` | Optional object ACL, e.g. `public-read` |

Call `get_publish_info()` to confirm `"backend": "s3"` and that the bucket is
reachable.

## RustFS via docker-compose (complete example)

[RustFS](https://rustfs.com/) is a self-hosted, S3-compatible object store. The
repo ships a ready-to-run compose file that brings up RustFS, creates the bucket
(public-read so `dest_url` works in a browser), and starts the MCP server wired
to publish into it:

- [`examples/docker-compose.rustfs.yml`](../examples/docker-compose.rustfs.yml)

```bash
# 1) Point the compose file's volume at your ComfyUI output directory
#    (edit the `comfyui-output` bind under the comfyui-mcp-server service).
# 2) Make sure ComfyUI is running on the host (port 8188).
# 3) Bring it up:
docker compose -f examples/docker-compose.rustfs.yml up
```

This exposes:

- **MCP endpoint** at `http://127.0.0.1:9100/mcp` (point your client here),
- **RustFS S3 API** at `http://127.0.0.1:9000`,
- **RustFS console** at `http://127.0.0.1:9001` (login `rustfsadmin` / `rustfsadmin`).

Generate an image, then `publish_asset(...)`; the returned `dest_url` will be a
`http://localhost:9000/comfy-assets/...` URL served by RustFS.

> The compose example sets `COMFY_MCP_FEATURES=all` so every tool group is
> available — handy for exploring. Drop or narrow it (e.g. `models,system`) for a
> leaner tool list.

## Custom workflows

Add custom workflows without rebuilding by mounting a directory over
`/app/workflows`:

```bash
# Bash (Linux / macOS)
-v /path/to/workflows:/app/workflows:ro
```

```powershell
# PowerShell (Windows)
-v C:\path\to\workflows:/app/workflows:ro
```

## Build locally

```bash
docker build -t comfyui-mcp-server .
docker run --rm -p 9000:9000 \
  -e COMFYUI_URL=http://host.docker.internal:8188 \
  --add-host=host.docker.internal:host-gateway \
  comfyui-mcp-server
```

## Security note

The container binds all interfaces on its port; only the host mapping you choose
with `-p` is reachable. Keep the published port bound to localhost (or behind a
reverse proxy with auth) — don't expose it to untrusted networks.
