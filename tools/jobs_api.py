"""Rich job ledger tools via /api/jobs (opt-in feature group: 'jobs_api').

ComfyUI 0.22+ exposes an /api/jobs ledger with per-job status, timing, output
previews, and the full workflow — richer than parsing /history. Availability is
version-dependent, so these tools surface clear errors when the endpoint is
absent.
"""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("MCP_Server")


def register_jobs_api_tools(mcp: FastMCP, comfyui_client):
    """Register /api/jobs ledger tools with the MCP server."""

    @mcp.tool()
    def list_jobs(limit: int = 20, status: Optional[str] = None) -> dict:
        """List recent jobs from ComfyUI's /api/jobs ledger.

        Returns per-job status, priority, create/start/end timestamps, output
        counts, and a preview output — a richer view than get_queue_status or
        raw history. (Requires a ComfyUI build that exposes /api/jobs.)

        Args:
            limit: Maximum number of jobs to return (default 20).
            status: Optional status filter (e.g. "completed", "running").

        Returns:
            Dict with 'jobs' and 'count', or an error dict.
        """
        try:
            data = comfyui_client.get_jobs(limit=limit, status=status)
            jobs = data.get("jobs", data) if isinstance(data, dict) else data
            return {"jobs": jobs, "count": len(jobs) if isinstance(jobs, list) else None}
        except Exception as e:
            logger.exception("Failed to list jobs")
            return {
                "error": str(e),
                "hint": "This ComfyUI build may not expose /api/jobs.",
            }

    @mcp.tool()
    def get_job_detail(job_id: str) -> dict:
        """Get the full record for one job from /api/jobs/{id}.

        Includes outputs, execution status/timing, and the submitted workflow —
        useful for provenance and debugging a specific run.

        Args:
            job_id: The job id from list_jobs.

        Returns:
            The job record dict, or an error dict.
        """
        try:
            return comfyui_client.get_job_detail(job_id)
        except Exception as e:
            logger.exception(f"Failed to get job detail for {job_id}")
            return {
                "error": str(e),
                "job_id": job_id,
                "hint": "This ComfyUI build may not expose /api/jobs/{id}.",
            }
