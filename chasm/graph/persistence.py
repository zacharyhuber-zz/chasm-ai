"""Graph persistence — load/save the ChasmGraph to JSON on disk."""

from __future__ import annotations

import json
from pathlib import Path

from networkx.readwrite import json_graph

from chasm.core.config import settings
from chasm.core.logger import get_logger

logger = get_logger(__name__)


def load_graph_from_disk(graph) -> None:
    """Load a previously exported graph if the file exists."""
    export_path = settings.export_path
    if export_path.exists():
        try:
            with export_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            graph.graph = json_graph.node_link_graph(data)
            logger.info(
                "Loaded graph from %s (%d nodes, %d edges)",
                export_path,
                graph.node_count,
                graph.edge_count,
            )
        except Exception as exc:
            logger.warning("Failed to load graph from disk: %s", exc)


def save_graph_to_disk(graph) -> None:
    """Persist the graph to JSON."""
    try:
        graph.export_graph(str(settings.export_path))
        logger.info("Graph saved to %s.", settings.export_path)
    except Exception as exc:
        logger.error("Failed to save graph: %s", exc)
