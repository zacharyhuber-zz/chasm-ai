"""ProductCataloger — discovers hardware products from company websites.

Scrapes a company page (and its linked sub-pages) with trafilatura and uses
Google Gemini to extract structured `Product` entities from the combined text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import trafilatura
from bs4 import BeautifulSoup

from chasm.core.config import settings
from chasm.core.llm import GeminiAgent
from chasm.core.logger import get_logger
from chasm.models.schema import Product

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt sent to the LLM for product extraction
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = (
    "You are a hardware product extractor. Analyze the following website text "
    "and identify all distinct physical hardware products sold by this company. "
    "Return ONLY a JSON list of objects with 'name' and 'description' keys. "
    "Do not include accessories, spare parts, or software-only offerings. "
    "If no products can be identified, return an empty list: []\n"
    "Example format: "
    '[{"name": "Widget Pro", "description": "A compact industrial sensor."}]'
)


class ProductCataloger(GeminiAgent):
    """Scrape a company website and extract `Product` entities via Gemini."""

    # ------------------------------------------------------------------
    # 1. Scrape — with sub-page discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract clean text from raw HTML via trafilatura."""
        return trafilatura.extract(html) or ""

    @staticmethod
    def _find_product_links(html: str, base_url: str, max_links: int = 8) -> list[str]:
        """Parse the homepage HTML to find likely product-page links."""
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        seen: set[str] = set()
        product_links: list[str] = []

        # Patterns that usually indicate product-related pages
        product_patterns = re.compile(
            r"/(product|drone|camera|robomaster|store|shop|mavic|phantom|inspire|mini|air|avata|neo|flip)",
            re.IGNORECASE,
        )

        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            full = urljoin(base_url, href)
            parsed = urlparse(full)

            # Stay on the same domain, skip anchors / duplicates
            if parsed.netloc != base_domain:
                continue
            path = parsed.path.rstrip("/")
            if path in seen or not path or path == "/":
                continue
            seen.add(path)

            if product_patterns.search(path):
                product_links.append(full)
                if len(product_links) >= max_links:
                    break

        return product_links

    def scrape_company_site(self, base_url: str) -> str:
        """Fetch and extract text from *base_url* and its product sub-pages.

        Returns:
            Combined cleaned text from all scraped pages.

        Raises:
            RuntimeError: If the base page could not be fetched.
        """
        logger.info("Scraping %s …", base_url)
        homepage_html = trafilatura.fetch_url(base_url)

        if homepage_html is None:
            raise RuntimeError(f"Failed to download content from {base_url}")

        # Extract text from the homepage
        texts: list[str] = []
        homepage_text = self._extract_text(homepage_html)
        if homepage_text:
            texts.append(homepage_text)
        logger.info("Homepage: %d chars", len(homepage_text))

        # Discover and scrape product sub-pages
        sub_links = self._find_product_links(homepage_html, base_url)
        logger.info("Found %d product-related sub-page(s) to scrape", len(sub_links))

        for link in sub_links:
            try:
                html = trafilatura.fetch_url(link)
                if html:
                    page_text = self._extract_text(html)
                    if page_text:
                        texts.append(page_text)
                        logger.info("  + %s → %d chars", link, len(page_text))
            except Exception as exc:
                logger.warning("  ✗ %s failed: %s", link, exc)

        combined = "\n\n---\n\n".join(texts)

        if not combined.strip():
            raise RuntimeError(f"No extractable text found at {base_url} or its sub-pages")

        logger.info("Total scraped text: %d chars from %d page(s)", len(combined), len(texts))
        return combined

    # ------------------------------------------------------------------
    # 2. Extract products via Gemini
    # ------------------------------------------------------------------

    def extract_products(
        self,
        site_text: str,
        base_url: str,
    ) -> List[Product]:
        """Send scraped text to Gemini and parse out `Product` objects.

        Args:
            site_text: Cleaned website text (from `scrape_company_site`).
            base_url: Original URL — stored on each `Product.url`.

        Returns:
            A list of validated `Product` models.
        """
        logger.info("Prompting Gemini (%s) to extract products …", self.model)

        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{_EXTRACTION_PROMPT}\n\nText:\n{site_text[:30_000]}",
        )

        raw = response.text or "[]"
        logger.debug("Raw Gemini response:\n%s", raw)

        # The model sometimes wraps JSON in markdown fences — strip them.
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        else:
            logger.error("No JSON array found in Gemini response:\n%s", raw)
            return []

        try:
            items: list[dict] = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Gemini returned unparseable JSON:\n%s", raw)
            return []

        products: List[Product] = []
        for item in items:
            product = Product(
                id=str(uuid4()),
                name=item.get("name", "Unknown Product"),
                description=item.get("description"),
                url=base_url,
            )
            products.append(product)

        logger.info("Extracted %d product(s) from Gemini response.", len(products))
        return products

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def discover(self, base_url: str) -> List[Product]:
        """End-to-end: scrape ➜ extract ➜ return products."""
        text = self.scrape_company_site(base_url)
        return self.extract_products(text, base_url)
