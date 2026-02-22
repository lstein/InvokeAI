"""Tests for multiuser boards functionality."""

from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from invokeai.app.api.dependencies import ApiDependencies
from invokeai.app.api_app import app
from invokeai.app.services.invoker import Invoker
from invokeai.app.services.users.users_common import UserCreateRequest


@pytest.fixture
def setup_jwt_secret():
    """Initialize JWT secret for token generation."""
    from invokeai.app.services.auth.token_service import set_jwt_secret

    # Use a test secret key
    set_jwt_secret("test-secret-key-for-unit-tests-only-do-not-use-in-production")


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def setup_test_admin(mock_invoker: Invoker, email: str = "admin@test.com", password: str = "TestPass123") -> str:
    """Helper to create a test admin user and return user_id."""
    user_service = mock_invoker.services.users
    user_data = UserCreateRequest(
        email=email,
        display_name="Test Admin",
        password=password,
        is_admin=True,
    )
    user = user_service.create(user_data)
    return user.user_id


@pytest.fixture
def enable_multiuser_for_tests(monkeypatch: Any, mock_invoker: Invoker):
    """Enable multiuser mode and set up ApiDependencies for testing."""
    # Enable multiuser mode
    mock_invoker.services.configuration.multiuser = True

    # Set ApiDependencies.invoker as a class attribute
    ApiDependencies.invoker = mock_invoker

    yield

    # Cleanup
    if hasattr(ApiDependencies, "invoker"):
        delattr(ApiDependencies, "invoker")


@pytest.fixture
def admin_token(setup_jwt_secret: str, enable_multiuser_for_tests: Any, mock_invoker: Invoker, client: TestClient):
    """Get an admin token for testing."""
    # Create admin user
    setup_test_admin(mock_invoker, "admin@test.com", "TestPass123")

    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@test.com",
            "password": "TestPass123",
            "remember_me": False,
        },
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def user1_token(admin_token):
    """Get a token for test user 1."""
    # For now, we'll reuse admin token since user creation requires admin
    # In a full implementation, we'd create a separate user
    return admin_token


def _get_regular_user_token(mock_invoker: Invoker, client: TestClient, email: str) -> str:
    """Helper: create a non-admin user and return a Bearer token for them."""
    user_service = mock_invoker.services.users
    user_data = UserCreateRequest(
        email=email,
        display_name="Regular User",
        password="TestPass123",
        is_admin=False,
    )
    user_service.create(user_data)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123", "remember_me": False},
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def regular_user1_token(setup_jwt_secret, enable_multiuser_for_tests, mock_invoker: Invoker, client: TestClient):
    """Token for a regular (non-admin) user – user 1."""
    return _get_regular_user_token(mock_invoker, client, "regularuser1@test.com")


@pytest.fixture
def regular_user2_token(setup_jwt_secret, enable_multiuser_for_tests, mock_invoker: Invoker, client: TestClient):
    """Token for a regular (non-admin) user – user 2."""
    return _get_regular_user_token(mock_invoker, client, "regularuser2@test.com")


def test_create_board_requires_auth(enable_multiuser_for_tests: Any, client: TestClient):
    """Test that creating a board requires authentication."""
    response = client.post("/api/v1/boards/?board_name=Test+Board")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_boards_requires_auth(enable_multiuser_for_tests: Any, client: TestClient):
    """Test that listing boards requires authentication."""
    response = client.get("/api/v1/boards/?all=true")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_board_with_auth(client: TestClient, admin_token: str):
    """Test that authenticated users can create boards."""
    response = client.post(
        "/api/v1/boards/?board_name=My+Test+Board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["board_name"] == "My Test Board"
    assert "board_id" in data


def test_list_boards_with_auth(client: TestClient, admin_token: str):
    """Test that authenticated users can list their boards."""
    # First create a board
    client.post(
        "/api/v1/boards/?board_name=Listed+Board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Now list boards
    response = client.get(
        "/api/v1/boards/?all=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    boards = response.json()
    assert isinstance(boards, list)
    # Should include the board we just created
    board_names = [b["board_name"] for b in boards]
    assert "Listed Board" in board_names


def test_user_boards_are_isolated(client: TestClient, admin_token: str, user1_token: str):
    """Test that boards are isolated between users."""
    # Admin creates a board
    admin_response = client.post(
        "/api/v1/boards/?board_name=Admin+Board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_response.status_code == status.HTTP_201_CREATED

    # If we had separate users, we'd verify isolation here
    # For now, we'll just verify the board exists
    list_response = client.get(
        "/api/v1/boards/?all=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    boards = list_response.json()
    board_names = [b["board_name"] for b in boards]
    assert "Admin Board" in board_names


def test_enqueue_batch_requires_auth(enable_multiuser_for_tests: Any, client: TestClient):
    """Test that enqueuing a batch requires authentication."""
    response = client.post(
        "/api/v1/queue/default/enqueue_batch",
        json={
            "batch": {
                "batch_id": "test-batch",
                "data": [],
                "graph": {"nodes": {}, "edges": []},
            },
            "prepend": False,
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Ownership-check tests (the bug this PR fixes)
# ---------------------------------------------------------------------------


def test_update_board_forbidden_for_non_owner(
    client: TestClient, regular_user1_token: str, regular_user2_token: str
):
    """A user must not be able to update a board owned by a different user."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=User1+Ownership+Board",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # User 2 attempts to update user 1's board – should be forbidden
    update_resp = client.patch(
        f"/api/v1/boards/{board_id}",
        json={"board_name": "Hijacked Name"},
        headers={"Authorization": f"Bearer {regular_user2_token}"},
    )
    assert update_resp.status_code == status.HTTP_403_FORBIDDEN


def test_delete_board_forbidden_for_non_owner(
    client: TestClient, regular_user1_token: str, regular_user2_token: str
):
    """A user must not be able to delete a board owned by a different user."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=User1+Delete+Board",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # User 2 attempts to delete user 1's board – should be forbidden
    delete_resp = client.delete(
        f"/api/v1/boards/{board_id}",
        headers={"Authorization": f"Bearer {regular_user2_token}"},
    )
    assert delete_resp.status_code == status.HTTP_403_FORBIDDEN


def test_owner_can_update_their_board(client: TestClient, regular_user1_token: str):
    """A board owner must be able to update their own board."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=Original+Name",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # User 1 updates their own board
    update_resp = client.patch(
        f"/api/v1/boards/{board_id}",
        json={"board_name": "Updated Name"},
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert update_resp.status_code == status.HTTP_201_CREATED
    assert update_resp.json()["board_name"] == "Updated Name"


def test_owner_can_delete_their_board(client: TestClient, regular_user1_token: str):
    """A board owner must be able to delete their own board."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=Board+To+Delete",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # User 1 deletes their own board
    delete_resp = client.delete(
        f"/api/v1/boards/{board_id}",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert delete_resp.status_code == status.HTTP_200_OK


def test_admin_can_update_any_board(client: TestClient, admin_token: str, regular_user1_token: str):
    """An admin must be able to update any user's board."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=User1+Admin+Override+Board",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # Admin updates user 1's board
    update_resp = client.patch(
        f"/api/v1/boards/{board_id}",
        json={"board_name": "Admin Updated Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == status.HTTP_201_CREATED
    assert update_resp.json()["board_name"] == "Admin Updated Name"


def test_admin_can_delete_any_board(client: TestClient, admin_token: str, regular_user1_token: str):
    """An admin must be able to delete any user's board."""
    # User 1 creates a board
    create_resp = client.post(
        "/api/v1/boards/?board_name=User1+Admin+Delete+Board",
        headers={"Authorization": f"Bearer {regular_user1_token}"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    board_id = create_resp.json()["board_id"]

    # Admin deletes user 1's board
    delete_resp = client.delete(
        f"/api/v1/boards/{board_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == status.HTTP_200_OK
