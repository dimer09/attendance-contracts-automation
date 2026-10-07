import pytest
import requests
import responses

from bpa.extract import api_client
from bpa.extract.api_client import ApiError, fetch_contracts

import logging

BASE_URL = "http://localhost:8000"
URL = f"{BASE_URL}/contracts"

CONTRACT = {
    "employee_id": "M001",
    "client": "Acme",
    "start_date": "2026-09-01",
    "end_date": "2026-12-31",
    "status": "active",
    "max_daily_hours": 10,
}


@pytest.fixture(autouse=True)
def recorded_sleeps(monkeypatch):
    delays = []
    monkeypatch.setattr(api_client.time, "sleep", delays.append)
    return delays


@responses.activate  
def test_returns_contracts_and_sends_key_and_timeout():
    responses.add(responses.GET, URL, json=[CONTRACT], status=200)

    contracts = fetch_contracts(BASE_URL, "secret-key", timeout=2.0)

    assert contracts[0].employee_id == "M001"
    request = responses.calls[0].request
    assert request.headers["X-API-Key"] == "secret-key"
    assert request.req_kwargs["timeout"] == 2.0  


@responses.activate
def test_retries_after_server_error(recorded_sleeps):
    responses.add(responses.GET, URL, status=500)                
    responses.add(responses.GET, URL, json=[CONTRACT], status=200)  

    contracts = fetch_contracts(BASE_URL, "key")

    assert len(contracts) == 1
    assert len(responses.calls) == 2
    assert recorded_sleeps == [1.0]


@pytest.mark.parametrize(
    "error", [requests.ConnectionError("down"), requests.Timeout("slow")]
)
@responses.activate
def test_retries_after_network_error(error):
    responses.add(responses.GET, URL, body=error) 
    responses.add(responses.GET, URL, json=[CONTRACT], status=200)

    assert len(fetch_contracts(BASE_URL, "key")) == 1


@responses.activate
def test_gives_up_after_max_attempts(recorded_sleeps):
    for _ in range(3):
        responses.add(responses.GET, URL, status=503)

    with pytest.raises(ApiError, match="unavailable after 3 attempts"):
        fetch_contracts(BASE_URL, "key", max_attempts=3)

    assert len(responses.calls) == 3
    assert recorded_sleeps == [1.0, 2.0]  


@responses.activate
def test_client_error_is_not_retried(recorded_sleeps):
    responses.add(responses.GET, URL, status=401)

    with pytest.raises(ApiError, match="HTTP 401"):
        fetch_contracts(BASE_URL, "wrong-key")

    assert len(responses.calls) == 1  
    assert recorded_sleeps == []


@responses.activate
def test_invalid_contract_stops_with_clear_error():
    bad = {**CONTRACT, "status": "actif"}
    responses.add(responses.GET, URL, json=[CONTRACT, bad], status=200)

    with pytest.raises(ApiError, match="position 1"):
        fetch_contracts(BASE_URL, "key")


@responses.activate
def test_payload_must_be_a_list():
    responses.add(responses.GET, URL, json={"error": "oops"}, status=200)

    with pytest.raises(ApiError, match="list"):
        fetch_contracts(BASE_URL, "key")


@responses.activate
def test_non_json_response_is_rejected():
    responses.add(responses.GET, URL, body="<html>maintenance</html>", status=200)

    with pytest.raises(ApiError, match="JSON"):
        fetch_contracts(BASE_URL, "key")

@responses.activate
def test_api_key_never_appears_in_logs(caplog):
    caplog.set_level(logging.WARNING)  
    responses.add(responses.GET, URL, status=500)
    responses.add(responses.GET, URL, json=[CONTRACT], status=200)

    fetch_contracts(BASE_URL, "test-key")

    assert "Retrying" in caplog.text                
    assert "super-secret-key" not in caplog.text   

@responses.activate
def test_contract_that_is_not_an_object_is_rejected():
    responses.add(responses.GET, URL, json=[CONTRACT, 42], status=200)

    with pytest.raises(ApiError, match="position 1"):
        fetch_contracts(BASE_URL, "key")