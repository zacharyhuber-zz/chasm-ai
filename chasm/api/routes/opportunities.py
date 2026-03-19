"""Opportunity & Persona API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from chasm.api.deps import get_graph
from chasm.core.logger import get_logger
from chasm.graph.persistence import save_graph_to_disk

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["opportunities"])


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

@router.get("/opportunities/{product_id}")
def list_opportunities(product_id: str):
    """Return all Opportunity nodes for a product, sorted by severity."""
    graph = get_graph()

    if not graph.graph.has_node(product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    opps = graph.get_opportunities(product_id)

    # Sort: High → Medium → Low
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    opps.sort(key=lambda o: severity_order.get(o.get("severity", "Low"), 3))

    return opps


@router.post("/opportunities/{product_id}/generate")
def generate_opportunities(product_id: str, background_tasks: BackgroundTasks):
    """Trigger opportunity + persona generation for a product."""
    graph = get_graph()

    if not graph.graph.has_node(product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = graph.graph.nodes[product_id]
    if product_data.get("node_type") != "Product":
        raise HTTPException(status_code=400, detail="Node is not a Product")

    product_name = product_data.get("name", product_id)

    def _run():
        from chasm.agents.synthesizer import OpportunityGenerator

        gen = OpportunityGenerator()

        # Clear existing opportunities and personas for this product
        _clear_node_type(graph, product_id, "HAS_OPPORTUNITY", "Opportunity")
        _clear_node_type(graph, product_id, "HAS_PERSONA", "Persona")

        # Generate new ones
        opportunities = gen.generate_opportunities(graph, product_id, product_name)
        for opp in opportunities:
            graph.add_opportunity(opp)

        personas = gen.generate_personas(graph, product_id, product_name, opportunities)
        for persona in personas:
            graph.add_persona(persona)

        save_graph_to_disk(graph)
        logger.info(
            "Generated %d opportunities and %d personas for '%s'.",
            len(opportunities),
            len(personas),
            product_name,
        )

    background_tasks.add_task(_run)
    return {"status": "generating", "product_id": product_id}


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

@router.get("/personas/{product_id}")
def list_personas(product_id: str):
    """Return all Persona nodes for a product."""
    graph = get_graph()

    if not graph.graph.has_node(product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    return graph.get_personas(product_id)


# ---------------------------------------------------------------------------
# Subgraph (for Evidence Drawer)
# ---------------------------------------------------------------------------

@router.get("/graph/subgraph")
def get_subgraph(node_ids: str):
    """Return a subgraph containing the specified nodes and their neighbours.

    Query param ``node_ids`` is a comma-separated list of node IDs.
    """
    ids = [nid.strip() for nid in node_ids.split(",") if nid.strip()]
    if not ids:
        return {"nodes": [], "links": []}

    graph = get_graph()
    return graph.get_subgraph(ids)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_node_type(graph, product_id: str, relation: str, node_type: str):
    """Remove all nodes of a given type linked to a product."""
    to_remove: list[str] = []
    for _, target, data in graph.graph.out_edges(product_id, data=True):
        if data.get("relation") == relation:
            node = graph.graph.nodes.get(target, {})
            if node.get("node_type") == node_type:
                to_remove.append(target)
    for nid in to_remove:
        graph.graph.remove_node(nid)
