"""Node schema introspection tools (opt-in feature group: 'nodes')."""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def _extract_enum(object_info: dict, class_type: str, field: str):
    """Pull an enum list (e.g. sampler_name) out of a node's required inputs."""
    node = object_info.get(class_type, {})
    required = node.get("input", {}).get("required", {})
    spec = required.get(field)
    # ComfyUI encodes enums as [[option, ...], {...}] or [[option, ...]].
    if isinstance(spec, list) and spec and isinstance(spec[0], list):
        return spec[0]
    return []


def register_node_tools(mcp: FastMCP, comfyui_client):
    """Register node-introspection tools with the MCP server."""

    @mcp.tool()
    def get_node_info(class_type: str) -> dict:
        """Get the input/output schema for a single ComfyUI node type.

        Use this to discover the valid parameters (and valid enum values) for a
        node before building or editing a workflow — e.g. the accepted models,
        samplers, or schedulers for a given node.

        Args:
            class_type: Node class name (e.g. "KSampler", "CheckpointLoaderSimple",
                "LoadImage", "ControlNetApply").

        Returns:
            The node's schema dict, or an error if the node type is unknown.
        """
        try:
            info = comfyui_client.get_object_info(class_type)
            if not info or class_type not in info:
                return {
                    "error": f"Unknown node type: '{class_type}'. "
                             f"Check the exact class name (case-sensitive)."
                }
            return info[class_type]
        except Exception as e:
            logger.exception(f"Failed to get node info for {class_type}")
            return {"error": str(e), "class_type": class_type}

    @mcp.tool()
    def list_samplers() -> dict:
        """List sampler names accepted by KSampler (e.g. euler, dpmpp_2m, ...).

        Lets an agent pick a valid sampler_name instead of guessing.
        """
        try:
            info = comfyui_client.get_object_info("KSampler")
            samplers = _extract_enum(info, "KSampler", "sampler_name")
            return {"samplers": samplers, "count": len(samplers)}
        except Exception as e:
            logger.exception("Failed to list samplers")
            return {"error": str(e)}

    @mcp.tool()
    def list_schedulers() -> dict:
        """List scheduler names accepted by KSampler (e.g. normal, karras, ...)."""
        try:
            info = comfyui_client.get_object_info("KSampler")
            schedulers = _extract_enum(info, "KSampler", "scheduler")
            return {"schedulers": schedulers, "count": len(schedulers)}
        except Exception as e:
            logger.exception("Failed to list schedulers")
            return {"error": str(e)}
