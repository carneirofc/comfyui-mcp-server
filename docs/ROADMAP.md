# Roadmap

Feature and integration roadmap for the ComfyUI MCP Server, oriented around one
goal: letting an LLM agent **operate** (generate, refine, vary) and **manage**
(monitor, control, maintain) a ComfyUI instance through reliable, discoverable
tools.

The roadmap is grounded in the live capability surface of ComfyUI (verified
against a running `0.22.0` instance) rather than the aspirational Comfy-Org
cloud `openapi.yaml`. Several cloud endpoints in that spec (`/api/assets`,
`/api/workflows`, `/api/auth/*`, `/api/user`, `/api/tasks`, `/api/nodes`) are
**not enabled** on a default local install (`"assets": false` in `/features`),
so we target the classic API plus the live `/api/jobs` ledger.

## Legend

- **Effort**: S (hours) · M (a day) · L (multi-day)
- **Status**: ✅ done · 🚧 in progress · ⬜ planned · 🔮 exploratory

> **Opt-in by default.** Phase 1 & 2 tools ship behind feature flags
> (`COMFY_MCP_FEATURES`) and are **off** unless enabled, so they don't bloat the
> tool list / LLM context. See [README → Optional Tool Groups](../README.md#optional-tool-groups-feature-flags).
> The **group** column below names the flag that enables each item.

---

## Current state (baseline)

The server today wraps 6 ComfyUI endpoints and exposes generation, viewing, job,
configuration, workflow, and publish tools (see [README](../README.md#available-tools)).

| Capability | Endpoint(s) used | Status |
|---|---|---|
| Queue a workflow | `POST /prompt` | ✅ |
| Poll completion | `GET /history[/{id}]` | ✅ |
| Queue status | `GET /queue` | ✅ |
| Cancel pending job | `POST /queue {delete}` | ✅ |
| Fetch asset | `GET /view` | ✅ |
| List checkpoints | `GET /object_info/CheckpointLoaderSimple` | ✅ |

**Structural gaps:** no input-image upload, model discovery limited to
checkpoints, no parameter/schema introspection, no system health/VRAM view, no
in-flight interrupt, no memory management.

---

## Phase 1 — Unblock core capability classes

*Goal: move from "text-to-image, guess the parameters" to "img2img / inpaint /
controlnet with discoverable, validated parameters." This is the highest-leverage
phase — each item removes a hard blocker, not a convenience.*

| # | Feature | Group | Tool(s) | Endpoint(s) | Effort | Status |
|---|---|---|---|---|---|---|
| 1.1 | **Input image upload** — enables img2img, inpainting, ControlNet, upscale | `upload` | `upload_image`, `upload_mask` | `POST /upload/image`, `POST /upload/mask` | M | ✅ |
| 1.2 | **Full model discovery** — loras, vae, controlnet, upscale, text_encoders, not just checkpoints | `models` | `list_model_folders`, `list_models_in_folder` | `GET /models`, `GET /models/{folder}` | S | ✅ |
| 1.3 | **Node schema introspection** — read valid enum values (samplers, schedulers, model slots) to build/validate workflows before submit | `nodes` | `get_node_info(class_type)`, `list_samplers`, `list_schedulers` | `GET /object_info/{class}` | M | ✅ |
| 1.4 | **Embeddings discovery** — textual-inversion tokens usable in prompts | `models` | `list_embeddings` | `GET /models/embeddings` | S | ✅ |

**Why first:** 1.1 alone unlocks every image-conditioned workflow class. 1.2 and
1.3 together let the agent self-correct (no more invalid `ckpt_name` / `sampler`
guesses), which directly reduces failed generations.

---

## Phase 2 — Real management & observability

*Goal: let the agent reason about the box's health and exert control, not just
fire-and-forget jobs.*

| # | Feature | Group | Tool(s) | Endpoint(s) | Effort | Status |
|---|---|---|---|---|---|---|
| 2.1 | **System stats** — VRAM/RAM free, GPU, ComfyUI/torch versions; capacity reasoning ("does this model fit?") | `system` | `get_system_stats` | `GET /system_stats` | S | ✅ |
| 2.2 | **Interrupt running job** — abort the *in-flight* job (distinct from deleting pending queue items) | `system` | `interrupt_job` | `POST /interrupt` | S | ✅ |
| 2.3 | **Free memory / unload models** — reclaim VRAM between heavy jobs | `system` | `free_memory(unload_models, free_memory)` | `POST /free` | S | ✅ |
| 2.4 | **Rich job ledger** — status, priority, timestamps, output previews, workflow_id; better backing for `list_assets`/`get_job` than parsing raw history | `jobs_api` | `list_jobs`, `get_job_detail` | `GET /api/jobs`, `GET /api/jobs/{id}` | M | ✅ |
| 2.5 | **Capability detection** — read `/features` so tools degrade gracefully (e.g. asset API on/off) | `system` | `get_capabilities` | `GET /features` | S | ✅ |

**Why:** 2.1–2.3 are the "manage the machine" trio. 2.4 upgrades the existing
job tools from history-parsing to a first-class ledger. 2.5 makes the server
robust across ComfyUI versions/configs.

---

## Phase 3 — Live progress & streaming

*Goal: replace fixed-interval history polling with real-time awareness.*

| # | Feature | Tool(s) / mechanism | Endpoint(s) | Effort | Status |
|---|---|---|---|---|---|
| 3.1 | **WebSocket progress** — subscribe to `/ws` for live execution/progress/preview events instead of polling `/history` | internal progress stream feeding `get_job` | `WS /ws` | L | 🔮 |
| 3.2 | **Streaming previews** — surface mid-generation preview frames to the agent | extend `view_image` | `/ws` binary previews, `supports_preview_metadata` | M | 🔮 |
| 3.3 | **Long-job UX** — progress percentage + ETA in `get_job` responses | derived from 3.1 | — | M | 🔮 |

**Why exploratory:** the current poll loop works; WebSocket is a reliability and
latency upgrade, not a blocker. Worth it once Phases 1–2 land.

---

## Phase 4 — Workflow lifecycle & reuse

*Goal: treat workflows as first-class, versioned, shareable assets.*

| # | Feature | Notes | Effort | Status |
|---|---|---|---|---|
| 4.1 | **Workflow validation (dry-run)** — validate a workflow against live `object_info` before queueing; return actionable errors | Builds on 1.3 | M | ⬜ |
| 4.2 | **Parameterized workflow templates** — extend `PARAM_*` system with typed constraints (min/max/enum) pulled from node schemas | Builds on 1.3 | M | ⬜ |
| 4.3 | **Workflow CRUD persistence** — save/list/version workflows via `/userdata` (local) since cloud `/api/workflows` is unavailable | `GET/POST /userdata`, `/api/v2/userdata` | M | 🔮 |
| 4.4 | **Workflow-from-image** — extract embedded workflow from a generated PNG to enable reproduce/remix | Parse PNG metadata | M | 🔮 |

---

## Phase 5 — Agent ergonomics & integrations

*Goal: make the server pleasant to drive from real agent stacks.*

| # | Feature | Notes | Effort | Status |
|---|---|---|---|---|
| 5.0 | **S3 publish backend** — publish to AWS S3, MinIO, or self-hosted RustFS instead of local disk | `COMFY_MCP_PUBLISH_BACKEND=s3` + `COMFY_MCP_S3_*`; see [README](../README.md#publish-to-s3-rustfs--minio--aws) | M | ✅ |
| 5.1 | **Persistent asset registry** — survive restart (current registry is ephemeral; see [Known Limitations](../README.md#known-limitations-v10)) | SQLite/JSON-backed | M | ⬜ |
| 5.2 | **Batch generation** — queue N variations (seed sweep / prompt matrix) in one call | Builds on job ledger | M | ⬜ |
| 5.3 | **Cost/time estimation** — predict job duration from steps × resolution × model and live VRAM | Builds on 2.1 | L | 🔮 |
| 5.4 | **Auth & multi-tenant** — optional bearer token / API key for non-localhost deploys | Pairs with the reverse-proxy guidance in README | M | 🔮 |
| 5.5 | **Client recipes** — documented configs for Claude Desktop, Cursor, n8n, LangGraph | Docs only | S | ⬜ |
| 5.6 | **Pluggable storage backends** — generalize the S3 abstraction (5.0) to GCS / Azure Blob / WebDAV | Builds on `managers/storage.py` | M | 🔮 |

---

## Suggested execution order

1. **1.2 → 1.3 → 1.4** (model + schema + embeddings discovery — small, compounding wins)
2. **1.1** (image upload — bigger, unlocks the most)
3. **2.1 → 2.2 → 2.3** (management trio — small, high operator value)
4. **2.4 → 2.5** (job ledger + capability detection)
5. Re-evaluate Phases 3–5 against real agent usage.

A focused **first batch** (ships value in ~1 day): `list_models(folder)`,
`get_node_info`, `get_system_stats`, `interrupt_job`, `free_memory` — five small
tools, mostly thin wrappers in `comfyui_client.py` + a new `tools/system.py`.
`upload_image` follows as its own slightly larger change.

---

## Endpoint reference (live-verified)

Endpoints confirmed available on ComfyUI `0.22.0` and targeted by this roadmap:

| Endpoint | Method | Used by phase |
|---|---|---|
| `/upload/image`, `/upload/mask` | POST | 1.1 |
| `/models`, `/models/{folder}` | GET | 1.2 |
| `/object_info`, `/object_info/{class}` | GET | 1.3, 4.1 |
| `/embeddings` | GET | 1.4 |
| `/system_stats` | GET | 2.1 |
| `/interrupt` | POST | 2.2 |
| `/free` | POST | 2.3 |
| `/api/jobs`, `/api/jobs/{id}` | GET | 2.4 |
| `/features` | GET | 2.5 |
| `/ws` | WS | 3.x |
| `/userdata`, `/api/v2/userdata` | GET/POST | 4.3 |

> Not targeted (disabled on default local installs): `/api/assets`,
> `/api/workflows`, `/api/auth/*`, `/api/user`, `/api/tasks`, `/api/nodes`.
> These belong to the Comfy-Org cloud API and would only apply to a hosted
> deployment.
