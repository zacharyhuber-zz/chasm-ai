"""ChasmGraph — Hardware-focused Knowledge Graph backed by NetworkX.

Manages Product → Component hierarchies and Source → Insight → Target
relationships as a directed graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

from chasm.core.logger import get_logger
from chasm.models.schema import Component, Insight, Product, Source

logger = get_logger(__name__)


class ChasmGraph:
    """Directed graph that models hardware feedback relationships.

    Node types: Product, Component, Source, Insight
    Edge relations: HAS_COMPONENT, YIELDS, ABOUT
    """

    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        logger.info("ChasmGraph initialised (empty).")

    # ------------------------------------------------------------------
    # Node methods
    # ------------------------------------------------------------------

    def add_product(self, product: Product) -> None:
        """Add a Product node to the graph."""
        attrs: dict[str, Any] = product.model_dump(mode="json")
        attrs["node_type"] = "Product"
        self.graph.add_node(product.id, **attrs)
        logger.info("Added Product node: %s (%s)", product.id, product.name)

    def add_component(self, component: Component, product_id: str) -> None:
        """Add a Component node and link it to its parent Product.

        Creates: Product —[HAS_COMPONENT]→ Component
        """
        attrs: dict[str, Any] = component.model_dump(mode="json")
        attrs["node_type"] = "Component"
        self.graph.add_node(component.id, **attrs)
        self.graph.add_edge(product_id, component.id, relation="HAS_COMPONENT")
        logger.info(
            "Added Component node: %s (%s) → linked to Product %s",
            component.id,
            component.name,
            product_id,
        )

    def add_source(self, source: Source) -> None:
        """Add a Source node to the graph."""
        attrs: dict[str, Any] = source.model_dump(mode="json")
        attrs["node_type"] = "Source"
        self.graph.add_node(source.id, **attrs)
        logger.info("Added Source node: %s (%s)", source.id, attrs["type"])

    # ------------------------------------------------------------------
    # Edge / connection method
    # ------------------------------------------------------------------

    def add_insight(self, insight: Insight, source_id: str, target_id: str) -> None:
        """Add an Insight node and wire it between a Source and a target.

        Creates:
            Source —[YIELDS]→ Insight —[ABOUT]→ Target (Product or Component)
        """
        attrs: dict[str, Any] = insight.model_dump(mode="json")
        attrs["node_type"] = "Insight"
        self.graph.add_node(insight.id, **attrs)

        # Source → Insight
        self.graph.add_edge(source_id, insight.id, relation="YIELDS")
        # Insight → Target (Product or Component)
        self.graph.add_edge(insight.id, target_id, relation="ABOUT")

        logger.info(
            "Added Insight node: %s | Source(%s) → Insight → Target(%s)",
            insight.id,
            source_id,
            target_id,
        )

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def get_product_hierarchy(self, product_id: str) -> list[dict[str, Any]]:
        """Return all Component nodes connected to a Product via HAS_COMPONENT.

        Returns:
            A list of node-attribute dicts for each child Component.
        """
        components: list[dict[str, Any]] = []
        for _, target, data in self.graph.out_edges(product_id, data=True):
            if data.get("relation") == "HAS_COMPONENT":
                node_data = dict(self.graph.nodes[target])
                components.append(node_data)
        return components

    def export_graph(self, filepath: str) -> None:
        """Persist the graph to a JSON file using NetworkX's node-link format."""
        data = json_graph.node_link_data(self.graph)
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        logger.info("Graph exported to %s (%d nodes, %d edges)", filepath, self.node_count, self.edge_count)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()

