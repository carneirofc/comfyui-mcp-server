"""Feature flags for optional MCP tool groups.

The core tool set (generation, viewing, jobs, configuration, workflows, publish)
is always registered. Additional tool groups are opt-in so the server doesn't
flood an LLM's context with tools the user hasn't asked for.

Enable groups via the ``COMFY_MCP_FEATURES`` environment variable — a
comma/space separated list of group names, or the special tokens ``all`` /
``none``::

    COMFY_MCP_FEATURES=models,system
    COMFY_MCP_FEATURES=all
    COMFY_MCP_FEATURES=none      # default

Group names map to registration functions in server.py.
"""

from typing import Dict, List, Set, Tuple

# group name -> human-readable description (tools it adds)
KNOWN_FEATURES: Dict[str, str] = {
    "models": (
        "Model & embedding discovery: list_model_folders, list_models_in_folder, "
        "list_embeddings"
    ),
    "nodes": (
        "Node schema introspection: get_node_info, list_samplers, list_schedulers"
    ),
    "upload": (
        "Input image/mask upload for img2img/inpaint/controlnet: upload_image, upload_mask"
    ),
    "system": (
        "System stats & runtime control: get_system_stats, interrupt_job, free_memory, "
        "get_capabilities"
    ),
    "jobs_api": (
        "Rich job ledger via /api/jobs: list_jobs, get_job_detail"
    ),
}

# Tokens that select every known feature / no features.
_ALL_TOKENS = {"all", "*"}
_NONE_TOKENS = {"none", "off", ""}


def parse_features(raw: str | None) -> Tuple[Set[str], List[str]]:
    """Parse a COMFY_MCP_FEATURES value into (enabled, unknown).

    Accepts comma- and/or whitespace-separated tokens, case-insensitive.
    ``all``/``*`` enables everything; ``none``/``off`` (or empty) enables
    nothing. Unknown tokens are returned separately so the caller can warn.
    """
    if not raw:
        return set(), []

    tokens = [t.strip().lower() for t in raw.replace(",", " ").split()]
    tokens = [t for t in tokens if t]

    if any(t in _ALL_TOKENS for t in tokens):
        return set(KNOWN_FEATURES), []

    enabled: Set[str] = set()
    unknown: List[str] = []
    for token in tokens:
        if token in _NONE_TOKENS:
            continue
        if token in KNOWN_FEATURES:
            enabled.add(token)
        else:
            unknown.append(token)
    return enabled, unknown
