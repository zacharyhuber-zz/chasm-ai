"""Chasm REST API — FastAPI application.

Exposes the Knowledge Graph, onboarding workflow, research pipeline,
and weekly briefings as HTTP endpoints.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chasm.api.deps import get_graph
from chasm.core.config import settings
from chasm.core.logger import get_logger
from chasm.graph.persistence import load_graph_from_disk, save_graph_to_disk

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lifespan (startup + shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load graph on startup, save on shutdown."""
    load_graph_from_disk(get_graph())
    logger.info("Chasm API started.")
    yield
    save_graph_to_disk(get_graph())
    logger.info("Chasm API shut down.")


# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Chasm API",
    description="AI-Powered Hardware Feedback Knowledge Graph",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow local dev and production deployment
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
_extra = settings.cors_origins
if _extra:
    _DEFAULT_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
from chasm.api.routes import interviews, onboarding, products, reports, research  # noqa: E402

app.include_router(products.router)
app.include_router(reports.router)
app.include_router(onboarding.router)
app.include_router(research.router)
app.include_router(interviews.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Simple health check endpoint."""
    graph = get_graph()
    return {
        "status": "ok",
        "graph_nodes": graph.node_count,
        "graph_edges": graph.edge_count,
    }
