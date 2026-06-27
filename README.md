# ComfyUI MCP Server

> Generate and refine AI images/audio/video through natural conversation

A lightweight MCP (Model Context Protocol) server that lets AI agents generate and iteratively refine images, audio, and video using a local ComfyUI instance.

You run the server, connect a client, and issue tool calls. Everything else is optional depth.

> **Fork notice:** This is a fork of [joenorton/comfyui-mcp-server](https://github.com/joenorton/comfyui-mcp-server) by [@joenorton](https://github.com/joenorton) (the original author). It adds Docker packaging, a configurable bind host/port, and Docker-aware publish paths. See the [CHANGELOG](CHANGELOG.md) for what's different.

---

## Quick Start (2–3 minutes)

This proves everything is working.

### 1) Clone and set up

This project uses [uv](https://docs.astral.sh/uv/) for dependency and environment management.

```bash
git clone https://github.com/carneirofc/comfyui-mcp-server.git
cd comfyui-mcp-server
uv sync
```

`uv sync` creates a virtual environment and installs all dependencies from `pyproject.toml` / `uv.lock`. Prefix commands with `uv run` to execute them inside that environment (no manual activation needed).

### 2) Start ComfyUI

Make sure ComfyUI is installed and running locally.

```bash
cd <ComfyUI_dir>
python main.py --port 8188
```

### 3) Run the MCP server

From the repository directory:

```bash
uv run python server.py
```

The server listens at:

```
http://127.0.0.1:9000/mcp
```

The bind address and port are configurable via `COMFY_MCP_HOST` (default `127.0.0.1`) and `COMFY_MCP_PORT` (default `9000`). For example, `COMFY_MCP_PORT=9999 uv run python server.py` serves at `http://127.0.0.1:9999/mcp`.

### 4) Verify it works (no AI client required)

Run the included test client:

```bash
# Use default prompt
uv run python test_client.py

# Or provide your own prompt
uv run python test_client.py -p "a beautiful sunset over mountains"
uv run python test_client.py --prompt "a cat on a mat"
```

`test_client.py` will:

* connect to the MCP server
* list available tools
* fetch and display server defaults (width, height, steps, model, etc.)
* run `generate_image` with your prompt (or a default)
* automatically use server defaults for all other parameters
* print the resulting asset information

If this step succeeds, the system is working.

**Note:** The test client respects server defaults configured via config files, environment variables, or `set_defaults` calls. Only the `prompt` parameter is required; all other parameters use server defaults automatically.

That’s it.

---

## Run with Docker

Prefer not to manage a local Python environment? A prebuilt, hardened image is published to the GitHub Container Registry on every push to `main`:

```
ghcr.io/carneirofc/comfyui-mcp-server:latest
```

The image is minimal (slim Python base, dependencies from the frozen `uv.lock`, no build tools) and runs as a non-root user. Images are also tagged by commit SHA (`sha-<short>`) and, for releases, by version (`vX.Y.Z`).

### Prerequisite

ComfyUI must be running and reachable **from inside the container**. The server checks ComfyUI on startup and exits if it can't connect.

### Run

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
- `COMFYUI_URL` points the server at your ComfyUI instance. `host.docker.internal` resolves to the Docker host; the `--add-host` flag is required on **Linux** (it's automatic with Docker Desktop on macOS/Windows).
- If ComfyUI runs in another container on the same Docker network, use that service name instead, e.g. `-e COMFYUI_URL=http://comfyui:8188` (and drop the `--add-host`).
- To map to a different **host** port, just change the left side of `-p` (e.g. `-p 9999:9000` serves at `http://127.0.0.1:9999/mcp`). To change the **container** port, set `-e COMFY_MCP_PORT=<port>` and match the right side of `-p` (e.g. `-e COMFY_MCP_PORT=9100 -p 9100:9100`); the in-container healthcheck honors `COMFY_MCP_PORT` automatically.

Then connect a client exactly as in [Use with an AI Agent](#use-with-an-ai-agent-cursor--claude--n8n) — the endpoint is identical.

### More: configuration, publishing, S3, and compose

The image is **feature-complete** — it bundles every optional dependency
(including `boto3` for the S3 backend), so all backends and tool groups work via
runtime env vars alone. For the full Docker reference — env-var table, enabling
optional tool groups, local-directory publishing, **publishing to S3 / MinIO /
RustFS**, and a ready-to-run **RustFS `docker-compose`** example — see:

- **[docs/DOCKER.md](docs/DOCKER.md)** — complete Docker guide
- **[examples/docker-compose.rustfs.yml](examples/docker-compose.rustfs.yml)** — RustFS + MCP server stack

> The container binds all interfaces on its port; only the host mapping you
> choose with `-p` is reachable. Keep it bound to localhost (or behind an
> authenticated reverse proxy) — don't expose it to untrusted networks.

---

## Use with an AI Agent (Cursor / Claude / n8n)

Once the server is running, you can connect it to an AI client.

Create a project-scoped `.mcp.json` file:

```json
{
  "mcpServers": {
    "comfyui-mcp-server": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

**Note:** Some clients use `"type": "http"` instead of `"streamable-http"`. Both work with this server. If auto-discovery doesn't work, try changing the type field.

Restart your AI client. You can now call tools such as:

* `generate_image`
* `view_image`
* `regenerate`
* `get_job`
* `list_assets`

This is the primary intended usage mode.

---

## What You Can Do After It Works

Once you’ve confirmed the server runs and a client can connect, the system supports:

* Iterative refinement via `regenerate` (no re-prompting)
* Explicit asset identity for reliable follow-ups
* Job polling and cancellation for long-running generations
* Optional image injection into the AI’s context (`view_image`)
* Auto-discovered ComfyUI workflows with parameter exposure
* Configurable defaults to avoid repeating common settings

Everything below builds on the same basic loop you just tested.

## Migration Notes (Previous Versions)

If you’ve used earlier versions of this project, a few things have changed.

### What’s the Same
- You still run a local MCP server that delegates execution to ComfyUI
- Workflows are still JSON files placed in the `workflows/` directory
- Image generation behavior is unchanged at its core

### What’s New
- **Streamable HTTP transport** replaces the older WebSocket-based approach
- **Explicit job management** (`get_job`, `get_queue_status`, `cancel_job`)
- **Asset identity** instead of ad-hoc URLs (stable across hostname changes)
- **Iteration support** via `regenerate` (replay with parameter overrides)
- **Optional visual feedback** for agents via `view_image`
- **Configurable defaults** to avoid repeating common parameters

### What Changed Conceptually
Earlier versions were a thin request/response bridge.
The current version is built around **iteration** and **stateful control loops**.

You can still generate an image with a single call, but you now have the option to:
- refer back to specific outputs
- refine results without re-specifying everything
- poll and cancel long-running jobs
- let AI agents inspect generated images directly

### Looking for the Old Behavior?
If you want the minimal, single-shot behavior from earlier versions:
- run `test_client.py` (this mirrors the original usage pattern)
- call `generate_image` with just a prompt (server defaults handle the rest)
- ignore the additional tools

No migration is required unless you want the new capabilities.

## Available Tools

### Generation Tools

- **`generate_image`**: Generate images (requires `prompt`)
- **`generate_song`**: Generate audio (requires `tags` and `lyrics`)
- **`regenerate`**: Regenerate an existing asset with optional parameter overrides (requires `asset_id`)

### Viewing Tools

- **`view_image`**: View generated images inline (images only, not audio/video)

### Job Management Tools

- **`get_queue_status`**: Check ComfyUI queue state (running/pending jobs) - provides async awareness
- **`get_job`**: Poll job completion status by prompt_id - check if a job has finished
- **`list_assets`**: Browse recently generated assets - enables AI memory and iteration
- **`get_asset_metadata`**: Get full provenance and parameters for an asset - includes workflow history
- **`cancel_job`**: Cancel a queued or running job

### Configuration Tools

- **`list_models`**: List available ComfyUI models
- **`get_defaults`**: Get current default values
- **`set_defaults`**: Set default values (with optional persistence)

### Workflow Tools

- **`list_workflows`**: List all available workflows
- **`run_workflow`**: Run any workflow with custom parameters

### Publish Tools

- **`get_publish_info`**: Show publish status (detected project root, publish dir, ComfyUI output root, and any missing setup)
- **`set_comfyui_output_root`**: Set ComfyUI output directory (recommended for Comfy Desktop / nonstandard installs; persisted across restarts)
- **`publish_asset`**: Publish a generated asset into the project's web directory with deterministic compression (default 600KB)

**Publish Notes:**
- **Session-scoped**: `asset_id`s are valid only for the current server session; restart invalidates them.
- **Zero-config in common cases**: Publish dir auto-detected (`public/gen`, `static/gen`, or `assets/gen`); if ComfyUI output can't be detected, set it once via `set_comfyui_output_root`.
- **Two modes**: Demo (explicit filename) and Library (auto filename + manifest update). In library mode, `manifest_key` is required.
- **Manifest**: Updated only when `manifest_key` is provided.
- **Compression**: Deterministic ladder to meet size limits; fails with a clear error if it can't.

**Quick Start:**

Example agent conversation flow:

**User:** "Generate a hero image for my website and publish it as hero.webp"

**Agent:** *Checks publish configuration*
- Calls `get_publish_info()` → sees status "ready"

**Agent:** *Generates image*
- Calls `generate_image(prompt="a hero image for a website")` → gets `asset_id`

**Agent:** *Publishes asset*
- Calls `publish_asset(asset_id="...", target_filename="hero.webp")` → success

**User:** "Now generate a logo and add it to the manifest as 'site-logo'"

**Agent:** *Generates and publishes with manifest*
- Calls `generate_image(prompt="a modern logo")` → gets `asset_id`
- Calls `publish_asset(asset_id="...", manifest_key="site-logo")` → auto-generates filename, updates manifest

See [docs/HOW_TO_TEST_PUBLISH.md](docs/HOW_TO_TEST_PUBLISH.md) for detailed usage and testing instructions.

### Publish to S3 (RustFS / MinIO / AWS)

By default `publish_asset` writes to a local project directory. You can instead
publish to any S3-compatible object store — including self-hosted **RustFS** and
**MinIO** — by setting `COMFY_MCP_PUBLISH_BACKEND=s3`. The publish tools behave
identically (same args, same compression ladder, same manifest); only the
destination changes. `dest_url` becomes the object's browser URL and `dest_path`
becomes its `s3://bucket/key` URI.

The S3 backend needs `boto3`, which is an optional dependency:

```bash
uv sync --group s3
```

Configure it with these environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `COMFY_MCP_PUBLISH_BACKEND` | `local` | Set to `s3` to upload instead of writing locally |
| `COMFY_MCP_S3_BUCKET` | — | **Required.** Target bucket name |
| `COMFY_MCP_S3_ENDPOINT_URL` | (AWS) | S3 endpoint, e.g. `http://localhost:9000` for RustFS/MinIO. Omit for AWS |
| `COMFY_MCP_S3_REGION` | `us-east-1` | Region |
| `COMFY_MCP_S3_ACCESS_KEY_ID` | `AWS_ACCESS_KEY_ID` | Access key (falls back to the standard AWS var) |
| `COMFY_MCP_S3_SECRET_ACCESS_KEY` | `AWS_SECRET_ACCESS_KEY` | Secret key (falls back to the standard AWS var) |
| `COMFY_MCP_S3_PREFIX` | `gen/` | Key prefix for published objects (and `manifest.json`) |
| `COMFY_MCP_S3_PUBLIC_BASE_URL` | (derived) | Base URL for `dest_url` (e.g. a CDN in front of the bucket) |
| `COMFY_MCP_S3_FORCE_PATH_STYLE` | `true` | Path-style addressing — **required for RustFS/MinIO** |
| `COMFY_MCP_S3_ACL` | (unset) | Optional object ACL, e.g. `public-read` (many S3-compatible servers ignore ACLs) |

**Example — publish to a local RustFS/MinIO instance:**

```bash
export COMFY_MCP_PUBLISH_BACKEND=s3
export COMFY_MCP_S3_ENDPOINT_URL=http://localhost:9000
export COMFY_MCP_S3_BUCKET=comfy-assets
export COMFY_MCP_S3_ACCESS_KEY_ID=minioadmin
export COMFY_MCP_S3_SECRET_ACCESS_KEY=minioadmin
export COMFY_MCP_S3_PUBLIC_BASE_URL=http://localhost:9000/comfy-assets
uv run python server.py
```

Call `get_publish_info()` to confirm the active backend (`"backend": "s3"`) and
that the bucket is reachable. The `COMFYUI_OUTPUT_ROOT` source still applies —
the server reads the rendered file locally, then uploads it.

> **Note:** the S3 source is still the local ComfyUI output directory, so
> `COMFYUI_OUTPUT_ROOT` (and, under Docker, mounting it) is required exactly as
> for local publishing. Only the publish *target* moves to S3.

**Using S3 from Docker.** The published image already includes `boto3`, so you
only pass the env vars. See **[docs/DOCKER.md → Publishing to S3](docs/DOCKER.md#publishing-to-s3--minio--rustfs)**
for `docker run` examples, and **[examples/docker-compose.rustfs.yml](examples/docker-compose.rustfs.yml)**
for a complete, ready-to-run RustFS + MCP server stack.

## Custom Workflows

Add custom workflows by placing JSON files in the `workflows/` directory. Workflows are automatically discovered and exposed as MCP tools.

### Workflow Placeholders

Use `PARAM_*` placeholders in workflow JSON to expose parameters:

- `PARAM_PROMPT` → `prompt: str` (required)
- `PARAM_INT_STEPS` → `steps: int` (optional)
- `PARAM_FLOAT_CFG` → `cfg: float` (optional)

**Example:**
```json
{
  "3": {
    "inputs": {
      "text": "PARAM_PROMPT",
      "steps": "PARAM_INT_STEPS"
    }
  }
}
```

The tool name is derived from the filename (e.g., `my_workflow.json` → `my_workflow` tool).

---

## Optional Tool Groups (Feature Flags)

To keep the tool list (and the LLM's context) lean, the server registers only a
**core** set of tools by default. Additional capabilities are grouped and are
**off unless you opt in** via the `COMFY_MCP_FEATURES` environment variable.

```bash
# Enable specific groups (comma or space separated)
COMFY_MCP_FEATURES=models,system uv run python server.py

# Enable everything
COMFY_MCP_FEATURES=all uv run python server.py

# Default — none of the optional groups
uv run python server.py
```

| Group | Adds tools | Useful for |
| --- | --- | --- |
| `models` | `list_model_folders`, `list_models_in_folder`, `list_embeddings` | Discovering loras, vae, controlnet, upscalers, embeddings (not just checkpoints) |
| `nodes` | `get_node_info`, `list_samplers`, `list_schedulers` | Reading a node's valid parameters/enums before building a workflow |
| `upload` | `upload_image`, `upload_mask` | Providing input images for img2img / inpaint / ControlNet |
| `system` | `get_system_stats`, `get_capabilities`, `interrupt_job`, `free_memory` | Health/VRAM checks and runtime control (stop in-flight job, unload models) |
| `jobs_api` | `list_jobs`, `get_job_detail` | A richer job ledger via ComfyUI's `/api/jobs` (status, timing, previews) |

Unknown group names are ignored with a warning. The enabled groups are logged at
startup. Changing the flag requires a server restart (it controls which tools are
registered).

> The core tools — generation, `view_image`, `regenerate`, job polling
> (`get_job`, `get_queue_status`, `cancel_job`), `list_assets`, configuration,
> workflows, and publishing — are always available regardless of this setting.

## Configuration

The server supports configurable defaults to avoid repeating common parameters. Defaults can be set via:

- **Runtime defaults**: Use `set_defaults` tool (ephemeral, lost on restart)
- **Config file**: `~/.config/comfy-mcp/config.json` (persistent)
- **Environment variables**: `COMFY_MCP_DEFAULT_*` prefixed variables

Defaults are resolved in priority order: per-call values → runtime defaults → config file → environment variables → hardcoded defaults.

For complete configuration details, see [docs/REFERENCE.md](docs/REFERENCE.md#parameters).

---

## Detailed Reference

Complete parameter lists, return schemas, configuration options, and advanced workflow metadata are documented in:

- **[API Reference](docs/REFERENCE.md)** - Complete tool reference, parameters, return values, and configuration
- **[Architecture](docs/ARCHITECTURE.md)** - Design decisions and system overview

## Project Structure

```
comfyui-mcp-server/
├── server.py              # Main entry point
├── comfyui_client.py      # ComfyUI API client
├── asset_processor.py     # Image processing utilities
├── test_client.py         # Test client
├── managers/              # Core managers
│   ├── workflow_manager.py
│   ├── defaults_manager.py
│   └── asset_registry.py
├── tools/                 # MCP tool implementations
│   ├── generation.py
│   ├── asset.py
│   ├── job.py             # Job management tools
│   ├── configuration.py
│   └── workflow.py
├── models/                # Data models
│   ├── workflow.py
│   └── asset.py
└── workflows/             # Workflow JSON files
    ├── generate_image.json
    └── generate_song.json
```

## Notes

- The server binds to localhost by default. Do not expose it publicly without authentication or a reverse proxy.
- Ensure your models exist in `<ComfyUI_dir>/models/checkpoints/`
- Server uses **streamable-http** transport (HTTP-based, not WebSocket)
- Workflows are auto-discovered - no code changes needed
- Assets expire after 24 hours (configurable)
- `view_image` only supports images (PNG, JPEG, WebP, GIF)
- Asset identity uses `(filename, subfolder, type)` instead of URL for robustness
- Full workflow history is stored for provenance and reproducibility
- `regenerate` uses stored workflow data to recreate assets with parameter overrides
- Session isolation: `list_assets` can filter by session for clean AI agent context

## Troubleshooting

**Server won't start:**
- Check ComfyUI is running on port 8188 (default)
- Verify Python 3.14+ is installed (`python --version`)
- Check all dependencies are installed: `uv sync`
- Check server logs for specific error messages

**Client can't connect:**
- Verify server shows "Server running at http://127.0.0.1:9000/mcp" in the console
- Test server directly: `curl http://127.0.0.1:9000/mcp` (should return MCP response)
- Check `.mcp.json` is in project root (or correct location for your client)
- Try both `"type": "streamable-http"` and `"type": "http"` - both are supported
- For Cursor-specific issues, see [docs/MCP_CONFIG_README.md](docs/MCP_CONFIG_README.md)

**Tools not appearing:**
- Check `workflows/` directory has JSON files with `PARAM_*` placeholders
- Check server logs for workflow parsing errors
- Verify ComfyUI has required custom nodes installed (if using custom workflows)
- Restart the MCP server after adding new workflows

**Asset not found errors:**
- Assets expire after 24 hours by default (configurable via `COMFY_MCP_ASSET_TTL_HOURS`)
- Assets are lost on server restart (ephemeral by design)
- Use `get_asset_metadata` to verify asset exists before using `regenerate`
- Check server logs to see if asset was registered successfully

## Known Limitations (v1.0)

- **Ephemeral asset registry**: `asset_id` references are only valid while the MCP server is running (and until TTL expiry). After restart, previously-issued `asset_id`s can’t be resolved, and regenerate will fail for those assets.

## Contributing

Issues and pull requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Acknowledgements

- [@joenorton](https://github.com/joenorton) - **original author**; this repository is a fork of [joenorton/comfyui-mcp-server](https://github.com/joenorton/comfyui-mcp-server)
- [@venetanji](https://github.com/venetanji) - streamable-http foundation & PARAM_* system

## Maintainer

- Fork: [@carneirofc](https://github.com/carneirofc)
- Original: [@joenorton](https://github.com/joenorton)

## License

Apache License 2.0 — Copyright 2026 Joe Norton. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
