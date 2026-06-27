"""System stats & runtime control tools (opt-in feature group: 'system')."""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_system_tools(mcp: FastMCP, comfyui_client):
    """Register system/management tools with the MCP server."""

    @mcp.tool()
    def get_system_stats() -> dict:
        """Get ComfyUI system stats: GPU, VRAM/RAM (total & free), and versions.

        Useful for capacity reasoning (does a model fit in free VRAM?) and health
        reporting.

        Returns:
            ComfyUI's /system_stats payload (system + devices), or an error dict.
        """
        try:
            return comfyui_client.get_system_stats()
        except Exception as e:
            logger.exception("Failed to get system stats")
            return {"error": str(e)}

    @mcp.tool()
    def get_capabilities() -> dict:
        """Get ComfyUI server capability flags (/features).

        Reports what the server supports (e.g. asset API on/off, max upload size).
        Helps tools degrade gracefully across ComfyUI versions/configs.
        """
        try:
            return comfyui_client.get_features()
        except Exception as e:
            logger.exception("Failed to get capabilities")
            return {"error": str(e)}

    @mcp.tool()
    def interrupt_job() -> dict:
        """Interrupt the job ComfyUI is currently executing.

        Distinct from cancel_job: this aborts the *in-flight* job rather than
        removing a pending queue item. No-op if nothing is running.
        """
        try:
            result = comfyui_client.interrupt()
            return {"status": "interrupted", **result}
        except Exception as e:
            logger.exception("Failed to interrupt job")
            return {"error": str(e)}

    @mcp.tool()
    def free_memory(unload_models: bool = True, free_memory: bool = True) -> dict:
        """Reclaim GPU/CPU memory by unloading models and/or freeing caches.

        Args:
            unload_models: Unload loaded models from VRAM (default True).
            free_memory: Free cached memory (default True).

        Returns:
            Status dict, or an error dict.
        """
        try:
            result = comfyui_client.free(unload_models=unload_models, free_memory=free_memory)
            return {
                "status": "freed",
                "unload_models": unload_models,
                "free_memory": free_memory,
                **result,
            }
        except Exception as e:
            logger.exception("Failed to free memory")
            return {"error": str(e)}
