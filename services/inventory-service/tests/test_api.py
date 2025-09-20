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

def test_inventory_pagination_and_filtering():
    # Prepare sample inventory
    items = [
        {"sku": "SKU100", "location": "store1", "quantity": 10},
        {"sku": "SKU100", "location": "store2", "quantity": 20},
        {"sku": "SKU200", "location": "store1", "quantity": 5},
        {"sku": "SKU300", "location": "store3", "quantity": 30},
        {"sku": "SKU400", "location": "store1", "quantity": 15},
    ]
    for item in items:
        client.post(f"/inventory/{item['sku']}/adjust", json=item)
    
    # Test: List all inventory, limit 2
    resp = client.get("/inventory?limit=2")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    # Test: Offset works
    resp2 = client.get("/inventory?limit=2&offset=2")
    assert resp2.status_code == 200
    assert resp2.json() != results  # Should be different due to offset

    # Test: Filter by SKU
    resp = client.get("/inventory?sku=SKU100")
    assert resp.status_code == 200
    sku100_results = resp.json()
    assert all(r["sku"] == "SKU100" for r in sku100_results)
    assert len(sku100_results) == 2

    # Test: Filter by location
    resp = client.get("/inventory?location=store1")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["location"] == "store1"

    # Test: Filter by min_quantity
    resp = client.get("/inventory?min_quantity=15")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["quantity"] >= 15

    # Test: Filter by max_quantity
    resp = client.get("/inventory?max_quantity=10")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["quantity"] <= 10

    # Test: Combined filters
    resp = client.get("/inventory?sku=SKU100&location=store2&min_quantity=15")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sku"] == "SKU100"
    assert data[0]["location"] == "store2"
    assert data[0]["quantity"] == 20