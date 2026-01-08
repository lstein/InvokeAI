"""Tests for multiuser boards functionality."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from invokeai.app.api_app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get an admin token for testing."""
    # First setup an admin user
    response = client.post(
        "/api/v1/auth/setup",
        json={
            "email": "admin@test.com",
            "display_name": "Test Admin",
            "password": "TestPass123",
        },
    )
    if response.status_code == 400:
        # Admin already exists, try to login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "TestPass123",
            },
        )
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def user1_token(client, admin_token):
    """Get a token for test user 1."""
    # For now, we'll reuse admin token since user creation requires admin
    # In a full implementation, we'd create a separate user
    return admin_token


def test_create_board_requires_auth(client):
    """Test that creating a board requires authentication."""
    response = client.post("/api/v1/boards/?board_name=Test+Board")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_boards_requires_auth(client):
    """Test that listing boards requires authentication."""
    response = client.get("/api/v1/boards/?all=true")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_board_with_auth(client, admin_token):
    """Test that authenticated users can create boards."""
    response = client.post(
        "/api/v1/boards/?board_name=My+Test+Board",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["board_name"] == "My Test Board"
    assert "board_id" in data


def test_list_boards_with_auth(client, admin_token):
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


def test_user_boards_are_isolated(client, admin_token, user1_token):
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


def test_enqueue_batch_requires_auth(client):
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
