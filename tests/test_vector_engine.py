"""Integration tests for VectorEngine — extracted from engine.py __main__ block."""

import pytest
from sklearn.metrics.pairwise import cosine_similarity

from chasm.vector.engine import VectorEngine


@pytest.fixture(scope="module")
def engine() -> VectorEngine:
    return VectorEngine()


def test_embedding_dimension(engine: VectorEngine):
    emb = engine.generate_embedding("Test sentence.")
    assert isinstance(emb, list)
    assert len(emb) > 0


def test_semantic_similarity(engine: VectorEngine):
    text_a = "The drone battery overheats quickly during flight."
    text_b = "Major thermal issues with the power cell."
    text_c = "The landing gear feels flimsy."

    emb_a = engine.generate_embedding(text_a)
    emb_b = engine.generate_embedding(text_b)
    emb_c = engine.generate_embedding(text_c)

    sim_ab = cosine_similarity([emb_a], [emb_b])[0][0]
    sim_ac = cosine_similarity([emb_a], [emb_c])[0][0]
    sim_bc = cosine_similarity([emb_b], [emb_c])[0][0]

    # Semantically similar texts should score higher
    assert sim_ab > sim_ac, f"A↔B ({sim_ab:.4f}) should be > A↔C ({sim_ac:.4f})"
    assert sim_ab > sim_bc, f"A↔B ({sim_ab:.4f}) should be > B↔C ({sim_bc:.4f})"
    assert sim_ab > 0.3, f"A↔B should be meaningfully high, got {sim_ab:.4f}"
