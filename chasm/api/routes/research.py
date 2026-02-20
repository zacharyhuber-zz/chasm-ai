"""Research-related API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from chasm.api.deps import get_graph
from chasm.workflows.pipeline import run_weekly_research

router = APIRouter(prefix="/api", tags=["research"])


@router.post("/research/{product_id}")
def trigger_research(product_id: str, background_tasks: BackgroundTasks):
    """Manually trigger the weekly research pipeline for a specific product.

    Runs in the background so the API responds immediately.
    """
    graph = get_graph()
    if product_id not in graph.graph:
        raise HTTPException(
            status_code=404, detail=f"Product '{product_id}' not in graph"
        )

    background_tasks.add_task(run_weekly_research, graph)
    return {
        "status": "research_started",
        "product_id": product_id,
        "message": "Pipeline is running in the background. Check /api/graph for updates.",
    }
