"""Input image/mask upload tools (opt-in feature group: 'upload').

Enables img2img, inpainting, and ControlNet workflows by letting an agent push
an input image (or mask) into ComfyUI's input directory, which a LoadImage node
can then reference.
"""

import base64
import binascii
import logging
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def _resolve_bytes(image_path: Optional[str], image_base64: Optional[str]):
    """Return (data, error). Exactly one source must be provided."""
    if bool(image_path) == bool(image_base64):
        return None, "Provide exactly one of image_path or image_base64."
    if image_path:
        if not os.path.isfile(image_path):
            return None, f"File not found: {image_path}"
        try:
            with open(image_path, "rb") as f:
                return f.read(), None
        except OSError as e:
            return None, f"Could not read file: {e}"
    try:
        return base64.b64decode(image_base64, validate=True), None
    except (binascii.Error, ValueError) as e:
        return None, f"Invalid base64 data: {e}"


def register_upload_tools(mcp: FastMCP, comfyui_client):
    """Register input-upload tools with the MCP server."""

    @mcp.tool()
    def upload_image(
        filename: str,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        subfolder: str = "",
        folder_type: str = "input",
        overwrite: bool = False,
    ) -> dict:
        """Upload an input image to ComfyUI (for img2img / inpaint / controlnet).

        Provide the image as either a local file path or base64 data. The
        returned {name, subfolder, type} is what a LoadImage node references.

        Args:
            filename: Target filename in ComfyUI's input dir (e.g. "ref.png").
            image_path: Path to a local image file (mutually exclusive with image_base64).
            image_base64: Base64-encoded image bytes (mutually exclusive with image_path).
            subfolder: Optional subfolder within the input directory.
            folder_type: "input" (default), "temp", or "output".
            overwrite: Overwrite an existing file with the same name.

        Returns:
            ComfyUI's upload response (name/subfolder/type), or an error dict.
        """
        data, err = _resolve_bytes(image_path, image_base64)
        if err:
            return {"error": err}
        try:
            result = comfyui_client.upload_image(
                data=data,
                filename=filename,
                subfolder=subfolder,
                folder_type=folder_type,
                overwrite=overwrite,
            )
            return {"status": "uploaded", **result}
        except Exception as e:
            logger.exception("Failed to upload image")
            return {"error": str(e)}

    @mcp.tool()
    def upload_mask(
        filename: str,
        original_filename: str,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        original_subfolder: str = "",
        original_type: str = "input",
        subfolder: str = "",
        folder_type: str = "input",
        overwrite: bool = False,
    ) -> dict:
        """Upload a mask paired with a previously uploaded input image.

        The mask is associated with an existing image (typically the result of a
        prior upload_image call) for inpainting workflows.

        Args:
            filename: Target mask filename.
            original_filename: Filename of the image this mask applies to.
            image_path: Path to a local mask file (mutually exclusive with image_base64).
            image_base64: Base64-encoded mask bytes (mutually exclusive with image_path).
            original_subfolder: Subfolder of the original image (default "").
            original_type: Folder type of the original image ("input" default).
            subfolder: Optional subfolder for the mask.
            folder_type: "input" (default), "temp", or "output".
            overwrite: Overwrite an existing mask with the same name.

        Returns:
            ComfyUI's upload response, or an error dict.
        """
        data, err = _resolve_bytes(image_path, image_base64)
        if err:
            return {"error": err}
        original_ref = {
            "filename": original_filename,
            "subfolder": original_subfolder,
            "type": original_type,
        }
        try:
            result = comfyui_client.upload_mask(
                data=data,
                filename=filename,
                original_ref=original_ref,
                subfolder=subfolder,
                folder_type=folder_type,
                overwrite=overwrite,
            )
            return {"status": "uploaded", **result}
        except Exception as e:
            logger.exception("Failed to upload mask")
            return {"error": str(e)}
