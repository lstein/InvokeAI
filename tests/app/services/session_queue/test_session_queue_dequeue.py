"""Tests for session queue dequeue() scheduling policies (FIFO and round_robin)."""

import uuid
from typing import Optional
from unittest.mock import MagicMock

import pytest

from invokeai.app.services.config.config_default import InvokeAIAppConfig
from invokeai.app.services.invoker import Invoker
from invokeai.app.services.session_queue.session_queue_sqlite import SqliteSessionQueue


def _make_invoker(mock_invoker: Invoker, multiuser: bool, session_queueing: str) -> Invoker:
    """Return a mock invoker whose configuration reflects the supplied multiuser/session_queueing settings."""
    config = MagicMock(spec=InvokeAIAppConfig)
    config.multiuser = multiuser
    config.session_queueing = session_queueing
    config.clear_queue_on_startup = False
    config.max_queue_size = 10000

    services = MagicMock()
    services.configuration = config
    services.events = mock_invoker.services.events
    services.logger = mock_invoker.services.logger

    invoker = MagicMock(spec=Invoker)
    invoker.services = services
    return invoker


@pytest.fixture
def session_queue(mock_invoker: Invoker) -> SqliteSessionQueue:
    """Create a SqliteSessionQueue backed by the mock invoker's in-memory database."""
    db = mock_invoker.services.board_records._db
    queue = SqliteSessionQueue(db=db)
    queue.start(mock_invoker)
    return queue


def _insert_queue_item(
    session_queue: SqliteSessionQueue,
    queue_id: str,
    user_id: str,
    priority: int = 0,
    item_id: Optional[int] = None,
) -> int:
    """Directly insert a minimal pending queue item and return its item_id."""
    session_id = str(uuid.uuid4())
    batch_id = str(uuid.uuid4())
    with session_queue._db.transaction() as cursor:
        if item_id is not None:
            cursor.execute(
                """--sql
                INSERT INTO session_queue (item_id, queue_id, session, session_id, batch_id, field_values, priority, workflow, origin, destination, retried_from_item_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, queue_id, "{}", session_id, batch_id, None, priority, None, None, None, None, user_id),
            )
        else:
            cursor.execute(
                """--sql
                INSERT INTO session_queue (queue_id, session, session_id, batch_id, field_values, priority, workflow, origin, destination, retried_from_item_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (queue_id, "{}", session_id, batch_id, None, priority, None, None, None, None, user_id),
            )
        return cursor.lastrowid  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# FIFO tests
# ---------------------------------------------------------------------------


def test_fifo_single_user_order(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """In FIFO mode, items are returned in item_id (creation) order for a single user."""
    queue_id = "default"
    invoker = _make_invoker(mock_invoker, multiuser=False, session_queueing="FIFO")
    session_queue.start(invoker)

    id1 = _insert_queue_item(session_queue, queue_id, "user_a")
    id2 = _insert_queue_item(session_queue, queue_id, "user_a")
    id3 = _insert_queue_item(session_queue, queue_id, "user_a")

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id1

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id2

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id3


def test_fifo_multi_user_order(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """In FIFO mode with multiple users, items are returned in global creation order."""
    queue_id = "default"
    invoker = _make_invoker(mock_invoker, multiuser=True, session_queueing="FIFO")
    session_queue.start(invoker)

    id_a1 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_a2 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_b1 = _insert_queue_item(session_queue, queue_id, "user_b")
    id_c1 = _insert_queue_item(session_queue, queue_id, "user_c")

    dequeued = []
    for _ in range(4):
        item = session_queue.dequeue()
        assert item is not None
        dequeued.append(item.item_id)

    assert dequeued == [id_a1, id_a2, id_b1, id_c1]


# ---------------------------------------------------------------------------
# round_robin tests (multiuser=True required)
# ---------------------------------------------------------------------------


def test_round_robin_basic(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """Round-robin with three users: one job from each user per round.

    Queue state:
        A job 1 (item_id lowest)
        A job 2
        B job 1
        C job 1
        C job 2
        A job 3

    Expected dequeue order: A1, B1, C1, A2, C2, A3
    """
    queue_id = "default"
    invoker = _make_invoker(mock_invoker, multiuser=True, session_queueing="round_robin")
    session_queue.start(invoker)

    id_a1 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_a2 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_b1 = _insert_queue_item(session_queue, queue_id, "user_b")
    id_c1 = _insert_queue_item(session_queue, queue_id, "user_c")
    id_c2 = _insert_queue_item(session_queue, queue_id, "user_c")
    id_a3 = _insert_queue_item(session_queue, queue_id, "user_a")

    expected = [id_a1, id_b1, id_c1, id_a2, id_c2, id_a3]
    for expected_id in expected:
        item = session_queue.dequeue()
        assert item is not None, "Queue unexpectedly empty"
        assert item.item_id == expected_id, f"Expected item_id={expected_id}, got item_id={item.item_id}"

    assert session_queue.dequeue() is None


def test_round_robin_single_user(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """Round-robin with a single user degenerates to FIFO for that user."""
    queue_id = "default"
    invoker = _make_invoker(mock_invoker, multiuser=True, session_queueing="round_robin")
    session_queue.start(invoker)

    id1 = _insert_queue_item(session_queue, queue_id, "user_a")
    id2 = _insert_queue_item(session_queue, queue_id, "user_a")
    id3 = _insert_queue_item(session_queue, queue_id, "user_a")

    for expected_id in [id1, id2, id3]:
        item = session_queue.dequeue()
        assert item is not None
        assert item.item_id == expected_id


def test_round_robin_ignored_in_single_user_mode(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """When multiuser=False, round_robin is ignored and FIFO is used instead."""
    queue_id = "default"
    # multiuser=False means FIFO regardless of session_queueing
    invoker = _make_invoker(mock_invoker, multiuser=False, session_queueing="round_robin")
    session_queue.start(invoker)

    id_a1 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_a2 = _insert_queue_item(session_queue, queue_id, "user_a")
    id_b1 = _insert_queue_item(session_queue, queue_id, "user_b")

    # FIFO order: a1, a2, b1 – NOT round-robin order (a1, b1, a2)
    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_a1

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_a2

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_b1


def test_round_robin_respects_priority_within_user(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """Within a user's queue, higher-priority items are served before lower-priority ones."""
    queue_id = "default"
    invoker = _make_invoker(mock_invoker, multiuser=True, session_queueing="round_robin")
    session_queue.start(invoker)

    # user_a: low-priority item enqueued first, then a high-priority item
    id_a_low = _insert_queue_item(session_queue, queue_id, "user_a", priority=0)
    id_a_high = _insert_queue_item(session_queue, queue_id, "user_a", priority=10)
    id_b1 = _insert_queue_item(session_queue, queue_id, "user_b", priority=0)

    # Round 0: user_a serves their highest-priority item (a_high), then user_b
    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_a_high

    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_b1

    # Round 1: user_a's remaining item
    item = session_queue.dequeue()
    assert item is not None
    assert item.item_id == id_a_low


def test_round_robin_empty_queue(session_queue: SqliteSessionQueue, mock_invoker: Invoker) -> None:
    """Dequeueing from an empty queue returns None in round_robin mode."""
    invoker = _make_invoker(mock_invoker, multiuser=True, session_queueing="round_robin")
    session_queue.start(invoker)

    assert session_queue.dequeue() is None
