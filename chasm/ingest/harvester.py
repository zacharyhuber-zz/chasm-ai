"""Harvesters — scrape review websites and Reddit into Markdown files.

Each harvester writes clean Markdown with YAML frontmatter to
``chasm/data/raw/{product_id}/`` for downstream ingestion.
"""

from __future__ import annotations


import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import praw
import trafilatura
import yaml

from chasm.core.config import settings
from chasm.core.logger import get_logger

logger = get_logger(__name__)


def _slugify(text: str, max_len: int = 80) -> str:
    """Turn arbitrary text into a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:max_len].rstrip("_")


# ======================================================================
# WebHarvester
# ======================================================================


class WebHarvester:
    """Scrape article/review URLs and save them as Markdown with frontmatter."""

    def scrape_url(self, url: str) -> str:
        """Fetch and extract the article body from a URL.

        Args:
            url: The page to scrape.

        Returns:
            Cleaned article text, or an empty string on failure.
        """
        logger.info("WebHarvester: fetching %s", url)
        html = trafilatura.fetch_url(url)
        if html is None:
            logger.warning("WebHarvester: could not download %s", url)
            return ""

        text = trafilatura.extract(html, include_comments=False)
        if not text:
            logger.warning("WebHarvester: no extractable text at %s", url)
            return ""

        logger.info("WebHarvester: extracted %d chars from %s", len(text), url)
        return text

    def save_to_markdown(self, url: str, text: str, product_id: str) -> Path:
        """Save scraped text as a Markdown file with YAML frontmatter.

        Args:
            url: Original source URL.
            text: Cleaned article body.
            product_id: Groups the file under ``chasm/data/raw/{product_id}/``.

        Returns:
            Path to the created file.
        """
        # Build a clean filename from the URL
        parsed = urlparse(url)
        slug = _slugify(f"{parsed.netloc}_{parsed.path}")
        filename = f"{slug}.md"

        out_dir = settings.raw_data_dir / product_id
        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / filename

        frontmatter = {
            "source_url": url,
            "source_type": "Review",
            "date_scraped": datetime.now(timezone.utc).isoformat(),
            "product_id": product_id,
        }

        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False).strip()}\n---\n\n{text}\n"

        filepath.write_text(content, encoding="utf-8")
        logger.info("WebHarvester: saved %s (%d bytes)", filepath, len(content))
        return filepath


# ======================================================================
# RedditHarvester
# ======================================================================


class RedditHarvester:
    """Scrape Reddit posts and comments, saving each as a Markdown file."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.reddit = praw.Reddit(
            client_id=client_id or settings.reddit_client_id,
            client_secret=client_secret or settings.reddit_client_secret,
            user_agent=user_agent or settings.reddit_user_agent,
        )
        logger.info("RedditHarvester ready (read-only=%s)", self.reddit.read_only)

    def scrape_subreddit(
        self,
        subreddit_name: str,
        product_id: str,
        search_term: str,
        limit: int = 10,
    ) -> list[Path]:
        """Search a subreddit, extract posts + top comments, save as Markdown.

        Args:
            subreddit_name: Name of the subreddit (without ``r/``).
            product_id: Groups files under ``chasm/data/raw/{product_id}/``.
            search_term: Query string (typically the product name).
            limit: Maximum number of posts to fetch.

        Returns:
            List of Paths to the created Markdown files.
        """
        logger.info(
            "RedditHarvester: searching r/%s for '%s' (limit=%d)",
            subreddit_name,
            search_term,
            limit,
        )

        subreddit = self.reddit.subreddit(subreddit_name)
        out_dir = settings.raw_data_dir / product_id
        out_dir.mkdir(parents=True, exist_ok=True)

        saved_files: list[Path] = []

        for submission in subreddit.search(search_term, limit=limit):
            # --- Build the body text ---
            body_parts: list[str] = []
            body_parts.append(f"# {submission.title}\n")

            if submission.selftext:
                body_parts.append(submission.selftext)

            # Top 5 comments
            submission.comment_sort = "top"
            submission.comments.replace_more(limit=0)
            top_comments = submission.comments[:5]

            if top_comments:
                body_parts.append("\n## Top Comments\n")
                for idx, comment in enumerate(top_comments, 1):
                    body_parts.append(
                        f"**Comment {idx}** (u/{comment.author}, score {comment.score}):\n"
                        f"> {comment.body}\n"
                    )

            full_text = "\n".join(body_parts)

            # --- Frontmatter ---
            frontmatter = {
                "source_url": f"https://reddit.com{submission.permalink}",
                "source_type": "Reddit",
                "subreddit": subreddit_name,
                "author": str(submission.author),
                "score": submission.score,
                "date_scraped": datetime.now(timezone.utc).isoformat(),
                "product_id": product_id,
            }

            content = f"---\n{yaml.dump(frontmatter, default_flow_style=False).strip()}\n---\n\n{full_text}\n"

            slug = _slugify(f"reddit_{subreddit_name}_{submission.id}")
            filepath = out_dir / f"{slug}.md"
            filepath.write_text(content, encoding="utf-8")
            saved_files.append(filepath)

            logger.info(
                "  + Saved post '%s' → %s (%d bytes)",
                submission.title[:50],
                filepath.name,
                len(content),
            )

        logger.info(
            "RedditHarvester: saved %d post(s) from r/%s",
            len(saved_files),
            subreddit_name,
        )
        return saved_files
