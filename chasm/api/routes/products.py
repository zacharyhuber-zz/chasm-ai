"""Product-related API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from chasm.api.deps import get_graph

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/products")
def list_products():
    """Return all Product nodes in the graph."""
    graph = get_graph()
    products: list[dict[str, Any]] = []
    for nid, data in graph.graph.nodes(data=True):
        if data.get("node_type") == "Product":
            products.append({
                "id": nid,
                "name": data.get("name", ""),
                "description": data.get("description"),
                "url": data.get("url"),
            })
    return products


@router.get("/graph")
def get_graph_data():
    """Return the full graph in node-link JSON format."""
    import json

    from networkx.readwrite import json_graph

    graph = get_graph()
    data = json_graph.node_link_data(graph.graph)
    return json.loads(json.dumps(data, default=str))
