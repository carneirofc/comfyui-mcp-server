"""Model & embedding discovery tools (opt-in feature group: 'models')."""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_model_tools(mcp: FastMCP, comfyui_client):
    """Register model-discovery tools with the MCP server."""

    @mcp.tool()
    def list_model_folders() -> dict:
        """List the model folder categories ComfyUI knows about.

        Returns category names like 'checkpoints', 'loras', 'vae', 'controlnet',
        'upscale_models', 'text_encoders', etc. Use list_models_in_folder to see
        the files in a given category.
        """
        try:
            folders = comfyui_client.get_models()
            return {"folders": folders, "count": len(folders)}
        except Exception as e:
            logger.exception("Failed to list model folders")
            return {"error": str(e)}

    @mcp.tool()
    def list_models_in_folder(folder: str) -> dict:
        """List model files within a specific folder category.

        This is how an agent discovers loras, vae, controlnet models, upscalers,
        etc. that a workflow can reference — not just checkpoints.

        Args:
            folder: Category name from list_model_folders (e.g. "loras", "vae",
                "controlnet", "upscale_models", "checkpoints").

        Returns:
            Dict with 'folder', 'models' (list of filenames), and 'count'.
        """
        try:
            models = comfyui_client.get_models(folder)
            return {"folder": folder, "models": models, "count": len(models)}
        except Exception as e:
            logger.exception(f"Failed to list models in folder {folder}")
            return {"error": str(e), "folder": folder}

    @mcp.tool()
    def list_embeddings() -> dict:
        """List textual-inversion embeddings available for use in prompts.

        Sourced from the 'embeddings' model folder (robust across instances where
        the /embeddings endpoint is overridden by a custom node).

        Returns:
            Dict with 'embeddings' (list of names) and 'count'.
        """
        try:
            embeddings = comfyui_client.get_models("embeddings")
            return {"embeddings": embeddings, "count": len(embeddings)}
        except Exception as e:
            logger.exception("Failed to list embeddings")
            return {"error": str(e)}
