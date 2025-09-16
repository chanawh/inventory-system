import pytest
from fastapi.testclient import TestClient
from src.main import app, init_db, DATABASE
import os

client = TestClient(app)

def setup_module(module):
    # Remove DB if exists, create fresh one
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    init_db()

def test_inventory_flow():
    sku = "SKU001"
    loc = "store1"
    # Add stock
    resp = client.post(f"/inventory/{sku}/adjust", json={"sku": sku, "location": loc, "quantity": 5})
    assert resp.status_code == 200
    # Get stock
    resp = client.get(f"/inventory/{sku}")
    assert resp.status_code == 200
    data = resp.json()
    assert data[loc] == 5
    # Remove stock
    resp = client.post(f"/inventory/{sku}/adjust", json={"sku": sku, "location": loc, "quantity": -3})
    assert resp.status_code == 200
    # Get stock, should be 2
    resp = client.get(f"/inventory/{sku}")
    assert resp.json()[loc] == 2
    # Try to remove too much
    resp = client.post(f"/inventory/{sku}/adjust", json={"sku": sku, "location": loc, "quantity": -5})
    assert resp.status_code == 400