"""Tests for interview session management and insight extraction."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chasm.interviews.sessions import (
    ChatMessage,
    InterviewSession,
    create_session,
    load_session,
    save_session,
    INTERVIEWS_DIR,
)


# ---------------------------------------------------------------------------
# InterviewSession model tests
# ---------------------------------------------------------------------------

class TestInterviewSessionModel:
    def test_default_fields(self):
        session = InterviewSession()
        assert len(session.id) == 12
        assert session.status == "pending"
        assert session.messages == []
        assert session.completed_at is None

    def test_message_creation(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp  # auto-filled

    def test_serialization_roundtrip(self):
        session = InterviewSession(id="test123")
        session.messages.append(ChatMessage(role="assistant", content="Hi"))
        session.messages.append(ChatMessage(role="user", content="Hello"))

        data = json.loads(session.model_dump_json())
        restored = InterviewSession(**data)

        assert restored.id == "test123"
        assert len(restored.messages) == 2
        assert restored.messages[0].role == "assistant"
        assert restored.messages[1].content == "Hello"


# ---------------------------------------------------------------------------
# File persistence tests
# ---------------------------------------------------------------------------

class TestSessionPersistence:
    @pytest.fixture(autouse=True)
    def _use_tmp(self, tmp_path, monkeypatch):
        """Redirect INTERVIEWS_DIR to a temp directory."""
        monkeypatch.setattr(
            "chasm.interviews.sessions.INTERVIEWS_DIR",
            tmp_path / "interviews",
        )
        self.tmp = tmp_path / "interviews"

    def test_create_and_load(self):
        session = create_session()
        loaded = load_session(session.id)
        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.status == "pending"

    def test_load_missing(self):
        assert load_session("nonexistent") is None

    def test_save_updates(self):
        session = create_session()
        session.status = "active"
        session.messages.append(ChatMessage(role="assistant", content="Welcome"))
        save_session(session)

        loaded = load_session(session.id)
        assert loaded is not None
        assert loaded.status == "active"
        assert len(loaded.messages) == 1


# ---------------------------------------------------------------------------
# Completion + graph injection tests (mocked LLM)
# ---------------------------------------------------------------------------

class TestSessionCompletion:
    @pytest.fixture(autouse=True)
    def _use_tmp(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "chasm.interviews.sessions.INTERVIEWS_DIR",
            tmp_path / "interviews",
        )

    @patch("chasm.graph.persistence.save_graph_to_disk")
    @patch("chasm.vector.engine.VectorEngine")
    @patch("chasm.agents.interviewer.InterviewInsightExtractor")
    def test_complete_injects_insights(
        self,
        MockExtractor,
        MockVectorEngine,
        mock_save_graph,
    ):
        from chasm.api.deps import get_graph
        from chasm.models.schema import Product, ComponentCategory, Component, Insight

        graph = get_graph()
        # Clear any state from other tests
        graph.graph.clear()
        graph.add_product(Product(id="p1", name="TestProduct"))

        # Create session with messages
        session = create_session()
        session.status = "active"
        session.messages = [
            ChatMessage(role="assistant", content="Welcome!"),
            ChatMessage(role="user", content="I think the battery is great."),
            ChatMessage(role="assistant", content="Tell me more."),
            ChatMessage(role="user", content="The firmware needs improvement."),
        ]
        save_session(session)

        # Mock the extractor to return typed results
        mock_instance = MockExtractor.return_value
        mock_instance.extract_from_transcript.return_value = [
            (
                Component(id="comp-test1", name="Battery", category=ComponentCategory.ELECTRICAL),
                Insight(id="ins-test1", summary="Battery is great", sentiment=0.8, tags=["battery"]),
                "TestProduct",
            ),
            (
                Component(id="comp-test2", name="Firmware", category=ComponentCategory.FIRMWARE),
                Insight(id="ins-test2", summary="Firmware needs work", sentiment=-0.5, tags=["firmware"]),
                "TestProduct",
            ),
        ]

        # Mock VectorEngine
        mock_ve_instance = MockVectorEngine.return_value
        mock_ve_instance.generate_embedding.return_value = [0.1] * 384
        mock_ve_instance.link_semantic_matches.return_value = 0

        injected = complete_session(session)

        assert injected == 2
        assert session.status == "completed"
        assert session.completed_at is not None

        # Verify insights were added to graph
        source_nodes = [
            (nid, d)
            for nid, d in graph.graph.nodes(data=True)
            if d.get("node_type") == "Source" and d.get("type") == "Employee_Interview"
        ]
        assert len(source_nodes) == 2

        # Clean up graph for other tests
        graph.graph.clear()


# Need to import complete_session after mocking
from chasm.interviews.sessions import complete_session
