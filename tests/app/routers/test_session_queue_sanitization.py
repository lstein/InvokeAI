"""Tests for session queue item sanitization in multiuser mode."""

import pytest

from invokeai.app.api.routers.session_queue import sanitize_queue_item_for_user
from invokeai.app.services.session_queue.session_queue_common import NodeFieldValue, SessionQueueItem
from invokeai.app.services.shared.graph import Graph, GraphExecutionState


@pytest.fixture
def sample_session_queue_item() -> SessionQueueItem:
    """Create a sample queue item with full data for testing."""
    graph = Graph()
    # Add a simple node to the graph
    from tests.test_nodes import PromptTestInvocation

    graph.add_node(PromptTestInvocation(id="test_node", prompt="test prompt"))

    session = GraphExecutionState(id="test_session", graph=graph)

    return SessionQueueItem(
        item_id=1,
        status="pending",
        batch_id="batch_123",
        session_id="session_123",
        queue_id="default",
        user_id="user_123",
        user_display_name="Test User",
        user_email="test@example.com",
        field_values=[
            NodeFieldValue(node_path="test_node", field_name="prompt", value="sensitive prompt data"),
        ],
        session=session,
        workflow=None,
    )


def test_sanitize_queue_item_for_admin(sample_session_queue_item):
    """Test that admins can see all data regardless of user_id."""
    result = sanitize_queue_item_for_user(
        queue_item=sample_session_queue_item,
        current_user_id="different_user",
        is_admin=True,
    )

    # Admin should see everything
    assert result.field_values is not None
    assert len(result.field_values) == 1
    assert result.session.graph.nodes is not None
    assert len(result.session.graph.nodes) == 1


def test_sanitize_queue_item_for_owner(sample_session_queue_item):
    """Test that queue item owners can see their own data."""
    result = sanitize_queue_item_for_user(
        queue_item=sample_session_queue_item,
        current_user_id="user_123",  # Same as queue item user_id
        is_admin=False,
    )

    # Owner should see everything
    assert result.field_values is not None
    assert len(result.field_values) == 1
    assert result.session.graph.nodes is not None
    assert len(result.session.graph.nodes) == 1


def test_sanitize_queue_item_for_different_user(sample_session_queue_item):
    """Test that non-admin users cannot see other users' sensitive data."""
    result = sanitize_queue_item_for_user(
        queue_item=sample_session_queue_item,
        current_user_id="different_user",
        is_admin=False,
    )

    # Non-admin viewing another user's item should have sanitized data
    assert result.field_values is None
    assert result.workflow is None
    # Session should be replaced with empty graph
    assert result.session.graph.nodes is not None
    assert len(result.session.graph.nodes) == 0
    # Session ID should be preserved
    assert result.session.id == "test_session"


def test_sanitize_preserves_non_sensitive_fields(sample_session_queue_item):
    """Test that sanitization preserves non-sensitive fields."""
    result = sanitize_queue_item_for_user(
        queue_item=sample_session_queue_item,
        current_user_id="different_user",
        is_admin=False,
    )

    # These fields should be preserved
    assert result.item_id == 1
    assert result.status == "pending"
    assert result.batch_id == "batch_123"
    assert result.session_id == "session_123"
    assert result.queue_id == "default"
    assert result.user_id == "user_123"
    assert result.user_display_name == "Test User"
    assert result.user_email == "test@example.com"
