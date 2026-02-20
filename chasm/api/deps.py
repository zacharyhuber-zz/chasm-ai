"""Shared dependencies for API route modules."""

from __future__ import annotations

from chasm.graph.builder import ChasmGraph

# Singleton graph instance shared across all route modules.
_graph = ChasmGraph()


def get_graph() -> ChasmGraph:
    """Return the global ChasmGraph instance."""
    return _graph
