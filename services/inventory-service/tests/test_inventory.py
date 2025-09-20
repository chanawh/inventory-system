import pytest
from fastapi.testclient import TestClient
from src.main import app
from main import app
from src.main import app
from main import app


client = TestClient(app)

def test_inventory_pagination():
    response = client.get("/inventory?limit=2&offset=0")
    print("Response JSON:", response.json())  # This will show the output in the test log
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 2