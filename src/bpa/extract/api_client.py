import logging
import time

import requests
from pydantic import ValidationError

from bpa.models import Contract

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Base class for API errors."""

def _parse_contact(response: requests.Response) -> list[Contract]:
    try:
        data = response.json()
    except ValueError as e:
        raise ApiError(f"Invalid JSON response: {e}") from e

    if not isinstance(data, list):
        raise ApiError(f"Expected a list of contracts, got: {type(data).__name__}")

    contracts = []
    for position, item in enumerate(data):
        try:
            contract = Contract(**item)
            contracts.append(contract)
        except (ValidationError, TypeError) as e:
            detail = e.errors()[0]['msg'] if isinstance(e, ValidationError) else str(e)
            raise ApiError(f"Error parsing contract at position {position}: {detail}") from e

    return contracts


def fetch_contracts(base_url: str, api_key: str, *, timeout : float = 5.0, max_attempts : int = 3, backoff_seconds : float = 1.0) -> list[dict]:
  
  
    url = base_url.rstrip("/") + "/contracts"
    headers = {"X-API-Key": api_key}
    last_problem = "No Attempts Made"
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except ( requests.ConnectionError, requests.Timeout) as e:
            last_problem = f"network error: {type(e).__name__}: {e}"
          
        else: 
            if response.status_code == 200:
                return _parse_contact(response)
            if response.status_code < 500:
                raise ApiError(f"HTTP {response.status_code}: {response.text}")
            if response.status_code >= 500:
                logger.warning(
                "Retrying request to %s after HTTP %s",
                url,
                response.status_code,
            )
            last_problem= f"server error: HTTP {response.status_code}: {response.text}"


        if attempt < max_attempts:
            delay = backoff_seconds * (2 ** (attempt - 1))
            logger.info(f"Attempt {attempt} failed. Retrying in {delay} seconds...")

            time.sleep(delay)

    raise ApiError(f"API unavailable after {max_attempts} attempts : {last_problem}")