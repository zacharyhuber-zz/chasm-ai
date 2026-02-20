"""VectorEngine — embedding generation and semantic linking for ChasmGraph.

Uses sentence-transformers to encode text into dense vectors and
scikit-learn to compute cosine similarity for discovering hidden
relationships between Insight nodes.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from chasm.core.config import settings
from chasm.core.logger import get_logger

logger = get_logger(__name__)


class VectorEngine:
    """Generate embeddings and discover semantic matches across Insight nodes."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("Loading embedding model: %s …", model_name)
        self.model = SentenceTransformer(model_name)
        logger.info("VectorEngine ready.")

    # ------------------------------------------------------------------
    # Core embedding method
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> list[float]:
        """Encode a single string into a dense vector.

        Args:
            text: The input text to embed.

        Returns:
            A Python list of floats representing the embedding.
        """
        vector: np.ndarray = self.model.encode(text, show_progress_bar=False)
        return vector.tolist()

    # ------------------------------------------------------------------
    # Semantic linking on the graph
    # ------------------------------------------------------------------

    def link_semantic_matches(
        self,
        nx_graph,
        threshold: float | None = None,
    ) -> int:
        """Find semantically similar Insight nodes and link them in the graph.

        Iterates over all nodes where ``node_type == "Insight"``, computes
        pairwise cosine similarity on their ``embedding`` vectors, and adds
        ``SEMANTIC_MATCH`` edges for pairs above *threshold*.

        Args:
            nx_graph: A ``networkx.DiGraph`` (typically ``ChasmGraph.graph``).
            threshold: Minimum cosine similarity to create an edge.

        Returns:
            The number of new SEMANTIC_MATCH edges added.
        """
        if threshold is None:
            threshold = settings.similarity_threshold

        # Collect Insight nodes that have embeddings
        insight_ids: list[str] = []
        embeddings: list[list[float]] = []

        for node_id, data in nx_graph.nodes(data=True):
            if data.get("node_type") == "Insight" and data.get("embedding"):
                insight_ids.append(node_id)
                embeddings.append(data["embedding"])

        if len(insight_ids) < 2:
            logger.info("Fewer than 2 embedded Insight nodes — nothing to link.")
            return 0

        # Compute pairwise cosine similarity
        matrix = cosine_similarity(np.array(embeddings))

        edges_added = 0
        n = len(insight_ids)
        for i in range(n):
            for j in range(i + 1, n):
                score = float(matrix[i, j])
                if score >= threshold:
                    nx_graph.add_edge(
                        insight_ids[i],
                        insight_ids[j],
                        relation="SEMANTIC_MATCH",
                        weight=round(score, 4),
                    )
                    logger.info(
                        "SEMANTIC_MATCH: %s ↔ %s (score=%.4f)",
                        insight_ids[i],
                        insight_ids[j],
                        score,
                    )
                    edges_added += 1

        logger.info(
            "Semantic linking complete: %d match(es) from %d Insight nodes.",
            edges_added,
            n,
        )
        return edges_added
