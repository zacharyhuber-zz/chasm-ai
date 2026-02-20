"""Onboarding workflow — discover and select products for the Knowledge Graph.

Interactive CLI that scrapes a company website, presents discovered products
to the user, and adds their selections to the ChasmGraph.
"""

from __future__ import annotations

import questionary

from chasm.agents.cataloger import ProductCataloger
from chasm.core.logger import get_logger
from chasm.graph.builder import ChasmGraph
from chasm.models.schema import Product

logger = get_logger(__name__)


def onboard_new_company(base_url: str, graph: ChasmGraph) -> list[Product]:
    """Discover products from a company website and let the user choose which to track.

    Args:
        base_url: Company homepage URL to scrape.
        graph: The ChasmGraph instance to add selected products to.

    Returns:
        The list of Product objects that were added to the graph.
    """
    print(f"\n{'='*60}")
    print(f"  Chasm · Company Onboarding")
    print(f"  Target: {base_url}")
    print(f"{'='*60}\n")

    # --- 1. Discover products ---
    cataloger = ProductCataloger()

    print("[1/3] Scraping website for products …")
    try:
        site_text = cataloger.scrape_company_site(base_url)
        print(f"      Extracted {len(site_text)} chars from {base_url}\n")
    except RuntimeError as exc:
        print(f"[✗] Scraping failed: {exc}")
        return []

    print("[2/3] Asking Gemini to identify products …")
    discovered = cataloger.extract_products(site_text, base_url)

    if not discovered:
        print("\n[!] No products were discovered on this website.")
        print("    Try a more specific URL (e.g., a /products page).\n")
        return []

    print(f"      Found {len(discovered)} product(s):\n")
    for i, p in enumerate(discovered, 1):
        desc = p.description or "(no description)"
        print(f"      {i}. {p.name} — {desc}")
    print()

    # --- 2. Interactive selection ---
    product_names = [p.name for p in discovered]

    selected_names = questionary.checkbox(
        "Select the products you want to track in your portfolio "
        "(Use Space to select, Enter to confirm):",
        choices=product_names,
    ).ask()

    # User pressed Ctrl-C or cancelled
    if selected_names is None:
        print("\n[!] Onboarding cancelled.\n")
        return []

    if not selected_names:
        print("\n[!] No products selected. Nothing was saved.\n")
        return []

    # --- 3. Filter and save to graph ---
    selected_products = [p for p in discovered if p.name in selected_names]

    print(f"\n[3/3] Adding {len(selected_products)} product(s) to the Knowledge Graph …\n")
    for product in selected_products:
        graph.add_product(product)
        print(f"      ✓ {product.name}  (id={product.id})")

    print(f"\n{'='*60}")
    print(f"  Onboarding complete — {len(selected_products)} product(s) saved")
    print(f"  Graph now has {graph.node_count} node(s), {graph.edge_count} edge(s)")
    print(f"{'='*60}\n")

    return selected_products
