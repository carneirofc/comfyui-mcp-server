# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This repository is a fork of
[joenorton/comfyui-mcp-server](https://github.com/joenorton/comfyui-mcp-server);
see [Acknowledgements](README.md#acknowledgements) for attribution.

## [Unreleased]

## [0.1.2] - 2026-06-27

### Added
- `CHANGELOG.md` following the Keep a Changelog format.
- Fork attribution crediting the original author,
  [@joenorton](https://github.com/joenorton), in the README and `NOTICE`.

## [0.1.1] - 2026-06-27

First tagged release of the fork.

### Fixed
- **Container HTTP endpoint is now reachable.** FastMCP defaulted its bind
  address to `127.0.0.1`, so inside the container the streamable-http
  transport only listened on container-localhost and the published port
  reset every connection. The bind host/port are now passed to FastMCP
  explicitly (the `FASTMCP_HOST` env var is a no-op in mcp 1.28.1).

### Added
- `COMFY_MCP_HOST` (default `127.0.0.1`) and `COMFY_MCP_PORT` (default `9000`)
  configuration variables. The Docker image sets `COMFY_MCP_HOST=0.0.0.0` so
  the published port works out of the box.
- The container healthcheck now probes `COMFY_MCP_PORT` instead of a
  hardcoded `9000`.
- Publish path environment variables (`COMFYUI_OUTPUT_ROOT`,
  `COMFY_MCP_PROJECT_ROOT`, `COMFY_MCP_PUBLISH_ROOT`) for running the publish
  tools under Docker.
- Hardened, multi-stage Docker image published to GHCR, with PowerShell and
  bash usage snippets for Windows users.

### Changed
- Migrated dependency management to [uv](https://docs.astral.sh/uv/) and
  dropped `requirements.txt`.

[Unreleased]: https://github.com/carneirofc/comfyui-mcp-server/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/carneirofc/comfyui-mcp-server/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/carneirofc/comfyui-mcp-server/releases/tag/v0.1.1
