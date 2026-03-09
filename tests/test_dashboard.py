"""Tests for FastAPI dashboard."""

import pytest
from fastapi.testclient import TestClient
from jjai_go2.dashboard.app import app


client = TestClient(app)


def test_dashboard_page_loads():
    """Dashboard HTML page loads."""
    response = client.get("/unitreego2")
    assert response.status_code == 200
    assert "JJAI Go2 Dashboard" in response.text
    assert "htmx" in response.text


def test_status_api_no_robot():
    """Status API returns disconnected when no robot."""
    response = client.get("/unitreego2/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False


def test_command_api_no_robot():
    """Command API returns error when no robot."""
    response = client.post(
        "/unitreego2/api/command",
        json={"command": "stand_up", "args": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


def test_voice_log_empty():
    """Voice log starts empty."""
    response = client.get("/unitreego2/api/voice-log")
    assert response.status_code == 200
    data = response.json()
    assert data["entries"] == []


def test_unknown_command():
    """Unknown commands return error."""
    response = client.post(
        "/unitreego2/api/command",
        json={"command": "nonexistent_command", "args": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
