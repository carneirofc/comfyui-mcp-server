# syntax=docker/dockerfile:1
#
# Minimalist, hardened image for the ComfyUI MCP server.
#
# - Multi-stage build: build tooling (uv) never reaches the final image.
# - Dependencies are installed from the frozen lockfile for reproducibility.
# - Final stage runs as an unprivileged user on a slim base with no build tools.
#
# Tip for maximum supply-chain hardening: pin the base images by digest, e.g.
#   FROM python:3.14-slim-bookworm@sha256:<digest> AS builder

############################
# Stage 1 — builder
############################
FROM python:3.14-slim-bookworm AS builder

# Pinned, statically-linked uv binary from its official (distroless) image.
COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install ONLY dependencies first so this layer is cached until the lockfile
# changes. The project itself is a non-package (package = false), so there is
# nothing else to install — deps land in /app/.venv.
#
# --all-groups installs every optional dependency group (currently `s3`, which
# bundles boto3) so the image is feature-complete: every backend and tool group
# works out of the box, gated only by runtime env vars. --no-dev still excludes
# test-only deps. New optional groups are picked up automatically.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-groups --no-install-project

############################
# Stage 2 — runtime
############################
FROM python:3.14-slim-bookworm AS runtime

# OCI image metadata (overridden/augmented by the CI metadata-action labels).
LABEL org.opencontainers.image.title="comfyui-mcp-server" \
      org.opencontainers.image.description="MCP server for generating and refining media via a ComfyUI instance" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/carneirofc/comfyui-mcp-server"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    # Bind all interfaces so the published port is reachable from the host;
    # without this FastMCP binds 127.0.0.1 inside the container and the
    # forwarded port resets connections.
    COMFY_MCP_HOST="0.0.0.0" \
    # HTTP transport port (9000 is the default; override at deploy).
    COMFY_MCP_PORT="9000" \
    # Default to the host's ComfyUI when run via `docker run`; override at deploy.
    COMFYUI_URL="http://host.docker.internal:8188"

# Create an unprivileged, no-login system user to run the server.
RUN groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --no-create-home --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# Bring in the pre-built virtualenv from the builder stage.
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Application source (only what the server needs at runtime).
COPY --chown=app:app server.py comfyui_client.py asset_processor.py feature_flags.py ./
COPY --chown=app:app managers ./managers
COPY --chown=app:app models ./models
COPY --chown=app:app tools ./tools
COPY --chown=app:app workflows ./workflows

# Drop privileges.
USER 10001:10001

# Streamable-HTTP transport listens here (see server.py). This is the default;
# override the runtime port with COMFY_MCP_PORT and publish it with `-p`.
EXPOSE 9000

# Liveness: confirm the server accepts TCP connections on its configured port.
# Shell form so $COMFY_MCP_PORT expands; probing the real port (not a hardcoded
# 127.0.0.1:9000) means a misconfigured bind shows up as unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,socket,sys; s=socket.socket(); s.settimeout(3); sys.exit(0 if s.connect_ex(('127.0.0.1',int(os.environ.get('COMFY_MCP_PORT','9000'))))==0 else 1)"

# Exec form so the process receives signals as PID 1.
CMD ["python", "server.py"]
