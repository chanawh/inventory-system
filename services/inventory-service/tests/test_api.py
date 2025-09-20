import os
import pytest
from fastapi.testclient import TestClient
from src.main import app, init_db, DATABASE

# --- Test Client & Helpers ---

client = TestClient(app)
API_KEY = os.environ.get("INVENTORY_API_KEY", "testkey")

def api_headers():
    return {"X-API-Key": API_KEY}

# --- Setup & Teardown ---

def setup_module(module):
    """Reset the database once before all tests in this module."""
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    init_db()

# --- Inventory Adjustment Flow ---

def test_inventory_flow():
    sku = "SKU001"
    loc = "store1"
    # Add stock
    resp = client.post(
        f"/inventory/{sku}/adjust",
        json={"sku": sku, "location": loc, "quantity": 5},
        headers=api_headers()
    )
    assert resp.status_code == 200
    # Get stock
    resp = client.get(f"/inventory/{sku}", headers=api_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data[loc] == 5
    # Remove stock
    resp = client.post(
        f"/inventory/{sku}/adjust",
        json={"sku": sku, "location": loc, "quantity": -3},
        headers=api_headers()
    )
    assert resp.status_code == 200
    # Get stock, should be 2
    resp = client.get(f"/inventory/{sku}", headers=api_headers())
    assert resp.json()[loc] == 2
    # Try to remove too much
    resp = client.post(
        f"/inventory/{sku}/adjust",
        json={"sku": sku, "location": loc, "quantity": -5},
        headers=api_headers()
    )
    assert resp.status_code == 400

# --- Inventory Pagination & Filtering ---

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
        client.post(
            f"/inventory/{item['sku']}/adjust",
            json=item,
            headers=api_headers()
        )
    
    # Test: List all inventory, limit 2
    resp = client.get("/inventory?limit=2", headers=api_headers())
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    # Test: Offset works
    resp2 = client.get("/inventory?limit=2&offset=2", headers=api_headers())
    assert resp2.status_code == 200
    assert resp2.json() != results  # Should be different due to offset

    # Test: Filter by SKU
    resp = client.get("/inventory?sku=SKU100", headers=api_headers())
    assert resp.status_code == 200
    sku100_results = resp.json()
    assert all(r["sku"] == "SKU100" for r in sku100_results)
    assert len(sku100_results) == 2

    # Test: Filter by location
    resp = client.get("/inventory?location=store1", headers=api_headers())
    assert resp.status_code == 200
    for r in resp.json():
        assert r["location"] == "store1"

    # Test: Filter by min_quantity
    resp = client.get("/inventory?min_quantity=15", headers=api_headers())
    assert resp.status_code == 200
    for r in resp.json():
        assert r["quantity"] >= 15

    # Test: Filter by max_quantity
    resp = client.get("/inventory?max_quantity=10", headers=api_headers())
    assert resp.status_code == 200
    for r in resp.json():
        assert r["quantity"] <= 10

    # Test: Combined filters
    resp = client.get("/inventory?sku=SKU100&location=store2&min_quantity=15", headers=api_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["sku"] == "SKU100"
    assert data[0]["location"] == "store2"
    assert data[0]["quantity"] == 20

# --- Simple Pagination Check ---

def test_inventory_pagination():
    """Simple pagination test: limit=2, offset=0 always returns at most 2 results, type is list."""
    resp = client.get("/inventory?limit=2&offset=0", headers=api_headers())
    print("Response JSON:", resp.json())
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) <= 2