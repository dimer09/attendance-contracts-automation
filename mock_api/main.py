

import json
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException

DATA_FILE = Path(__file__).parent.parent / "data" / "sample" / "contracts.json"

API_KEY= os.environ.get("MOCK_API_KEY", "dev-key")

app = FastAPI(title="Mock Contracts API", version="1.0.0")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    provided = (x_api_key or "").encode()
    if not secrets.compare_digest(provided, API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/health", tags=["Health Check"])
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/contracts", tags=["Contracts"], dependencies=[Depends(require_api_key)])
def list_contracts() -> list[dict]:
    return json.loads(DATA_FILE.read_text())