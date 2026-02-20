"""Master research pipeline — orchestrates all Chasm agents.

Iterates over every Product in the graph, discovers sources, scrapes them,
extracts insights, and finally runs semantic linking across the entire graph.
"""

from __future__ import annotations


from chasm.agents.extractor import InsightExtractor
from chasm.agents.scout import SourceScout
from chasm.core.config import settings
from chasm.core.logger import get_logger
from chasm.graph.builder import ChasmGraph
from chasm.ingest.harvester import RedditHarvester, WebHarvester
from chasm.models.schema import Source, SourceType
from chasm.vector.engine import VectorEngine

logger = get_logger(__name__)


def run_weekly_research(graph: ChasmGraph) -> None:
    """Execute the full weekly research pipeline across all tracked products.

    Steps:
        1. For each Product node → discover subreddits & review sites (SourceScout)
        2. Scrape discovered sources → save as Markdown (Harvesters)
        3. Extract Insights + Components from Markdown (InsightExtractor)
        4. Inject everything into the ChasmGraph
        5. Run semantic linking across all Insight nodes (VectorEngine)

    Args:
        graph: The ChasmGraph to read Products from and write results into.
    """
    logger.info("=" * 60)
    logger.info("  Weekly Research Pipeline — STARTING")
    logger.info("=" * 60)

    # --- Collect all Product nodes ---
    product_nodes = [
        (nid, data)
        for nid, data in graph.graph.nodes(data=True)
        if data.get("node_type") == "Product"
    ]

    if not product_nodes:
        logger.warning("No Product nodes in the graph. Nothing to research.")
        print("[!] No products in the graph. Run --onboard first.")
        return

    logger.info("Found %d product(s) to research.", len(product_nodes))

    # --- Initialize agents ---
    scout = SourceScout()
    web_harvester = WebHarvester()
    reddit_harvester = RedditHarvester()
    extractor = InsightExtractor()

    # --- Process each product ---
    for product_id, product_data in product_nodes:
        product_name = product_data.get("name", product_id)
        logger.info("-" * 40)
        logger.info("Processing: %s (id=%s)", product_name, product_id)

        raw_dir = settings.raw_data_dir / product_id
        raw_dir.mkdir(parents=True, exist_ok=True)

        # ---- Step 1: Discover sources ----
        logger.info("[Scout] Identifying sources for '%s' …", product_name)
        subreddits = scout.identify_subreddits(product_name)
        review_sites = scout.find_review_sites(product_name)

        logger.info("  Subreddits: %s", subreddits)
        logger.info("  Review sites: %s", review_sites)

        # ---- Step 2a: Scrape review sites ----
        for site_url in review_sites:
            full_url = f"https://{site_url}" if not site_url.startswith("http") else site_url
            try:
                text = web_harvester.scrape_url(full_url)
                if text:
                    web_harvester.save_to_markdown(full_url, text, product_id)
            except Exception as exc:
                logger.warning("  Web scrape failed for %s: %s", full_url, exc)

        # ---- Step 2b: Scrape Reddit ----
        for sub in subreddits:
            sub_name = sub.replace("r/", "").strip()
            try:
                reddit_harvester.scrape_subreddit(
                    subreddit_name=sub_name,
                    product_id=product_id,
                    search_term=product_name,
                    limit=5,
                )
            except Exception as exc:
                logger.warning("  Reddit scrape failed for r/%s: %s", sub_name, exc)

        # ---- Step 3: Extract insights ----
        logger.info("[Extractor] Processing scraped files for '%s' …", product_name)
        results = extractor.process_directory(
            raw_dir=str(raw_dir),
            product_id=product_id,
            product_name=product_name,
        )

        # ---- Step 4: Inject into graph ----
        logger.info("[Graph] Adding %d (Component, Insight) pairs …", len(results))
        for component, insight, source_url in results:
            # Add the component (linked to the product)
            graph.add_component(component, product_id=product_id)

            # Create a Source node for the URL
            source = Source(
                id=f"src-{insight.id}",
                type=SourceType.REVIEW,
                raw_text=insight.summary,
                url=source_url,
            )
            graph.add_source(source)

            # Add the Insight, linked from Source and pointing to Component
            graph.add_insight(
                insight=insight,
                source_id=source.id,
                target_id=component.id,
            )

        logger.info(
            "Product '%s' complete: graph now has %d nodes, %d edges.",
            product_name,
            graph.node_count,
            graph.edge_count,
        )

    # ---- Step 5: Semantic linking ----
    logger.info("=" * 40)
    logger.info("[VectorEngine] Generating embeddings and linking …")

    vector_engine = VectorEngine()

    # Generate embeddings for all Insight nodes that don't have them yet
    for nid, data in graph.graph.nodes(data=True):
        if data.get("node_type") == "Insight" and not data.get("embedding"):
            summary = data.get("summary", "")
            if summary:
                embedding = vector_engine.generate_embedding(summary)
                graph.graph.nodes[nid]["embedding"] = embedding

    matches = vector_engine.link_semantic_matches(graph.graph)
    logger.info("Semantic linking added %d SEMANTIC_MATCH edge(s).", matches)

    # ---- Done ----
    logger.info("=" * 60)
    logger.info("  Weekly Research Pipeline Complete.")
    logger.info("  Graph: %d nodes, %d edges", graph.node_count, graph.edge_count)
    logger.info("=" * 60)

    print(f"\n✓ Weekly Research Pipeline Complete.")
    print(f"  Graph: {graph.node_count} nodes, {graph.edge_count} edges\n")
