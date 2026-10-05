import pytest
from fastapi.testclient import TestClient

from bpa.models import Contract
from mock_api import main


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "API_KEY", "test-key")
    return TestClient(main.app)


def test_health_is_open(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_contracts_without_key_is_rejected(client):
    assert client.get("/contracts").status_code == 401


def test_contracts_with_wrong_key_is_rejected(client):
    response = client.get("/contracts", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_contracts_with_valid_key_returns_data(client):
    response = client.get("/contracts", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_api_data_is_valid_for_our_model(client):
    response = client.get("/contracts", headers={"X-API-Key": "test-key"})
    contracts = [Contract(**item) for item in response.json()]
    assert contracts[0].employee_id == "M001"