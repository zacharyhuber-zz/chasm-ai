"""Integration tests for ChasmGraph — extracted from builder.py __main__ block."""

from pathlib import Path

import pytest

from chasm.graph.builder import ChasmGraph
from chasm.models.schema import (
    Component,
    ComponentCategory,
    Insight,
    Product,
    Source,
    SourceType,
)


@pytest.fixture
def populated_graph() -> ChasmGraph:
    """Build a small graph with one product, component, source, and insight."""
    g = ChasmGraph()

    product = Product(
        id="prod-001",
        name="DJI Mavic 3 Pro",
        description="A triple-camera drone with Hasselblad optics.",
        url="https://www.dji.com",
    )
    battery = Component(
        id="comp-001",
        name="Intelligent Flight Battery",
        category=ComponentCategory.ELECTRICAL,
    )
    reddit_thread = Source(
        id="src-001",
        type=SourceType.REDDIT,
        raw_text="My Mavic 3 Pro overheats badly after 10 min of 4K recording.",
        url="https://reddit.com/r/dji/comments/abc123",
    )
    overheat_insight = Insight(
        id="ins-001",
        summary="Device overheats during extended 4K video recording.",
        sentiment=-0.8,
        tags=["overheating", "4K", "battery"],
    )

    g.add_product(product)
    g.add_component(battery, product_id="prod-001")
    g.add_source(reddit_thread)
    g.add_insight(overheat_insight, source_id="src-001", target_id="comp-001")
    return g


def test_nodes_exist(populated_graph: ChasmGraph):
    assert "prod-001" in populated_graph.graph
    assert "comp-001" in populated_graph.graph
    assert "src-001" in populated_graph.graph
    assert "ins-001" in populated_graph.graph


def test_node_types(populated_graph: ChasmGraph):
    assert populated_graph.graph.nodes["prod-001"]["node_type"] == "Product"
    assert populated_graph.graph.nodes["comp-001"]["node_type"] == "Component"
    assert populated_graph.graph.nodes["src-001"]["node_type"] == "Source"
    assert populated_graph.graph.nodes["ins-001"]["node_type"] == "Insight"


def test_edges(populated_graph: ChasmGraph):
    g = populated_graph
    assert g.graph.has_edge("prod-001", "comp-001")
    assert g.graph["prod-001"]["comp-001"]["relation"] == "HAS_COMPONENT"
    assert g.graph.has_edge("src-001", "ins-001")
    assert g.graph["src-001"]["ins-001"]["relation"] == "YIELDS"
    assert g.graph.has_edge("ins-001", "comp-001")
    assert g.graph["ins-001"]["comp-001"]["relation"] == "ABOUT"


def test_hierarchy(populated_graph: ChasmGraph):
    hierarchy = populated_graph.get_product_hierarchy("prod-001")
    assert len(hierarchy) == 1
    assert hierarchy[0]["name"] == "Intelligent Flight Battery"


def test_counts(populated_graph: ChasmGraph):
    assert populated_graph.node_count == 4
    assert populated_graph.edge_count == 3


def test_export(populated_graph: ChasmGraph, tmp_path: Path):
    export_path = tmp_path / "test_graph.json"
    populated_graph.export_graph(str(export_path))
    assert export_path.exists()
